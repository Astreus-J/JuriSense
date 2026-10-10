"""Login lockout after repeated failed attempts, with a Redis-backed window."""

import redis.asyncio as aioredis


class LoginLockout:
    def __init__(self, redis: aioredis.Redis, max_attempts: int, lockout_seconds: int) -> None:
        self._redis = redis
        self._max_attempts = max_attempts
        self._lockout_seconds = lockout_seconds

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @property
    def lockout_seconds(self) -> int:
        return self._lockout_seconds

    def _fail_key(self, email: str) -> str:
        return f"login:fail:{email}"

    def _lock_key(self, email: str) -> str:
        return f"login:lock:{email}"

    async def seconds_until_unlock(self, email: str) -> int | None:
        ttl = await self._redis.ttl(self._lock_key(email))
        return ttl if ttl > 0 else None

    async def reserve_attempt(self, email: str) -> int:
        """Security review (2026-10-05, concurrent-burst bypass): this used to be
        `register_failure`, called only AFTER a password was confirmed wrong. That let a
        burst of truly parallel requests for the same email all pass `seconds_until_unlock`
        before any of them incremented the counter, so an attacker with enough parallelism
        got more real password checks per burst than `max_attempts` -- the count itself was
        atomic, but it ran too late to gate anything.

        Calling this BEFORE password verification closes that: `INCR` is atomic, so a burst
        of N concurrent callers gets back N distinct, strictly increasing integers with no
        duplicates and no gaps, regardless of how the requests interleave at the network
        level. The caller must treat a returned value `> max_attempts` as "budget already
        exhausted by earlier attempts -- don't verify the password at all" (`login()` does
        this), which caps real verification attempts at exactly `max_attempts` per window no
        matter how many requests arrive concurrently. A value `<= max_attempts` still lets
        this specific request proceed to verification (including the exact attempt that
        reaches `max_attempts` and arms the lock for every later request) -- unchanged from
        the pre-fix semantics for the sequential case.

        Also closes the separate crash-recovery gap (`EXPIRE ... NX` on every call, not just
        the first, so a counter left without a TTL by an earlier crash self-heals on the very
        next call that touches it, per the original M2 fix) in the same atomic step.

        Security review (2026-10-05): the pre-fix `register_failure` deleted `fail_key` the
        instant the lock armed. That delete can't come back -- doing it here would let a
        genuinely concurrent straggler's own `INCR` restart the counter at 1, reopening the
        exact bypass this method exists to close. But leaving `fail_key` alone (simply not
        deleting it) opens a DIFFERENT gap: `fail_key`'s TTL is armed once, at the FIRST
        failure (`EXPIRE ... NX`), while `lock_key`'s TTL is armed at the `max_attempts`-th
        failure -- strictly later in every real episode -- so `lock_key` always expires
        before `fail_key` does. An attacker who times their own initial failures to spread
        across most of the window can land one single, ordinary, non-concurrent extra
        request in that gap: it sees `lock_key` already expired (not locked), but `fail_key`
        is still alive and already over budget, so it gets rejected -- yet as a side effect
        re-arms `lock_key` for a FRESH full `lockout_seconds`, for the price of one Redis
        round trip. Repeatable, cheap, and entirely attacker-timed; left unbounded this
        roughly doubles (and, repeated, keeps extending) the real lockout duration. Forcing
        (not `NX`) `fail_key`'s own TTL back to `lockout_seconds` in lockstep with `lock_key`
        every time this branch runs closes the gap: the two keys always expire at the exact
        same instant, so by the time either is gone, both are, and the next call to this
        method genuinely starts a fresh count at 1 -- never from a stale, artificially-
        surviving counter.
        """
        fail_key = self._fail_key(email)
        attempts = await self._redis.incr(fail_key)
        await self._redis.expire(fail_key, self._lockout_seconds, nx=True)
        if attempts >= self._max_attempts:
            await self._redis.set(self._lock_key(email), "1", ex=self._lockout_seconds)
            await self._redis.expire(fail_key, self._lockout_seconds)
        return attempts

    async def reset(self, email: str) -> None:
        """Full wipe -- the correct semantic only for a GENUINE successful login (the true
        owner just proved current control, so the whole slate resets), never for "undo the
        one reservation this request just made." See `undo_reservation` for that case."""
        await self._redis.delete(self._fail_key(email))

    async def undo_reservation(self, email: str) -> None:
        """QA/security review (2026-10-05): gives back exactly the one slot this request's
        own `reserve_attempt` call just reserved, without disturbing any OTHER,
        concurrently-in-flight reservation for the same email. `reset` (a full delete) is
        the wrong tool for this -- e.g. an inactive account's own correct-password login
        calling `reset` instead of this would erase an attacker's independently-accumulating
        failure count for the same email, handing them a fresh full budget for free every
        time the real owner happens to retry. Safe to call only right after this exact
        request's own `reserve_attempt` incremented the same key, which guarantees it
        currently exists and is >= 1."""
        await self._redis.decr(self._fail_key(email))
