"""Security review M2 (2026-10-03): regression tests for the TTL race in `LoginLockout`.

True concurrency can't be reproduced hermetically against fakeredis -- its async commands
resolve synchronously with no real interleaving (confirmed against `fakeredis/aioredis.py`'s
`can_read(timeout=0)` always finding the response already queued), so `asyncio.gather` over
several `register_failure` calls runs them sequentially in practice, which never reproduces
the bug either before or after the fix. Each test below instead forces the exact state a
crash mid-`register_failure` would leave -- a raw `INCR` with no matching `EXPIRE` -- by
calling `LoginLockout`'s methods and the underlying Redis client directly, the same pattern
`tests/approvals/test_concurrency.py` uses for its own un-reproducible races.
"""

from fakeredis import FakeAsyncRedis

from app.identity.infrastructure.lockout import LoginLockout

EMAIL = "attacker@example.com"
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900


async def _lockout() -> tuple[LoginLockout, FakeAsyncRedis]:
    redis = FakeAsyncRedis(decode_responses=True)
    return LoginLockout(redis, max_attempts=MAX_ATTEMPTS, lockout_seconds=LOCKOUT_SECONDS), redis


async def test_a_counter_left_without_ttl_is_repaired_by_the_next_failure() -> None:
    """Forces the exact state a crash between INCR and EXPIRE would leave: a failure
    counter with no TTL. The next registered failure must arm the TTL, not skip it because
    attempts is no longer 1 -- this is the case the pre-fix `if attempts == 1: expire(...)`
    missed."""
    lockout, redis = await _lockout()

    # Simulate the crash: an INCR happened, but its EXPIRE never ran.
    await redis.incr(lockout._fail_key(EMAIL))
    assert await redis.ttl(lockout._fail_key(EMAIL)) == -1  # no TTL, would never clear

    await lockout.register_failure(EMAIL)

    ttl = await redis.ttl(lockout._fail_key(EMAIL))
    assert ttl > 0, "the counter must carry a TTL after any register_failure call"


async def test_ttl_is_repaired_even_when_the_crash_happened_several_failures_in() -> None:
    """The pre-fix code only ever armed the TTL on the call that saw attempts == 1, so a key
    left without one several failures into the climb -- not just on the very first attempt --
    would stay TTL-less until the counter happened to reset. `EXPIRE ... NX` must run on every
    failure, not only the first, for this to self-heal regardless of where the crash lands."""
    lockout, redis = await _lockout()
    fail_key = lockout._fail_key(EMAIL)

    # Three raw increments with no EXPIRE at all, as repeated crashes would leave it.
    for _ in range(3):
        await redis.incr(fail_key)
    assert await redis.ttl(fail_key) == -1

    await lockout.register_failure(EMAIL)  # attempts becomes 4, still below MAX_ATTEMPTS

    assert await redis.ttl(fail_key) > 0


async def test_reset_after_repaired_ttl_clears_the_counter() -> None:
    """Sanity check, not a differentiator for the M2 bug itself (`reset` is a plain DELETE,
    untouched by the fix, and would pass against the pre-fix code too): a successful login
    must still clear a counter whose TTL was repaired by the fix above."""
    lockout, redis = await _lockout()
    await redis.incr(lockout._fail_key(EMAIL))  # pre-existing, TTL-less counter
    await lockout.register_failure(EMAIL)

    await lockout.reset(EMAIL)

    assert await redis.get(lockout._fail_key(EMAIL)) is None
