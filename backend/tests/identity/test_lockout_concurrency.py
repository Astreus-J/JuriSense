"""Security review M2 (2026-10-03) and its two 2026-10-05 follow-ups: regression tests for
the TTL race and the concurrent-burst bypass in `LoginLockout`.

True concurrency can't be reproduced hermetically against fakeredis -- its async commands
resolve synchronously with no real interleaving (confirmed against `fakeredis/aioredis.py`'s
`can_read(timeout=0)` always finding the response already queued), so `asyncio.gather` over
several `reserve_attempt` calls runs them sequentially in practice, which never reproduces a
race either before or after a fix. Each test below instead either forces the exact state a
crash would leave (a raw `INCR` with no matching `EXPIRE`) or calls `reserve_attempt`
sequentially the same number of times a burst would call it concurrently -- since the method
is built entirely from atomic Redis primitives (`INCR`, `EXPIRE ... NX`, `SET ... EX`), the
VALUES it returns under sequential calls are identical to what concurrent calls would produce
(Redis's own single-threaded command execution guarantees each `INCR` is globally ordered and
unique regardless of arrival order), even though the *timing/interleaving* can't be
reproduced. This is the same pattern `tests/approvals/test_concurrency.py` uses for its own
un-reproducible races.
"""

from unittest.mock import patch

import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import security
from app.identity.application import auth_service
from app.identity.domain.constants import Plan
from app.identity.domain.errors import AccountLockedError
from app.identity.infrastructure.lockout import LoginLockout

EMAIL = "attacker@example.com"
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900


async def _lockout() -> tuple[LoginLockout, FakeAsyncRedis]:
    redis = FakeAsyncRedis(decode_responses=True)
    return LoginLockout(redis, max_attempts=MAX_ATTEMPTS, lockout_seconds=LOCKOUT_SECONDS), redis


# ---- Concurrent-burst bypass (security review, 2026-10-05) ----


async def test_reserve_attempt_returns_strictly_increasing_counts() -> None:
    """The core property the burst-bypass fix depends on: `INCR` gives every caller a
    distinct, correctly-ordered integer, so N "concurrent" callers (simulated here
    sequentially, per the module docstring) can never collide on the same count."""
    lockout, _ = await _lockout()

    counts = [await lockout.reserve_attempt(EMAIL) for _ in range(10)]

    assert counts == list(range(1, 11))


async def test_only_the_first_max_attempts_calls_are_within_budget() -> None:
    """`login()` treats a return value `> max_attempts` as "don't even verify the password" --
    this is the actual bypass fix: in a burst of 10 concurrent wrong-password attempts, at
    most `max_attempts` (5) of them may proceed to `verify_password` at all, which this
    asserts directly against the values `reserve_attempt` hands back, with no dependency on
    being able to reproduce real concurrency."""
    lockout, _ = await _lockout()

    within_budget = []
    for _ in range(10):
        attempts = await lockout.reserve_attempt(EMAIL)
        within_budget.append(attempts <= lockout.max_attempts)

    assert within_budget == [True, True, True, True, True, False, False, False, False, False]


async def test_the_lock_is_armed_by_the_attempt_that_reaches_max_attempts_not_later() -> None:
    """The lock must exist by the time the `max_attempts`-th caller returns -- a burst's
    later callers (6th onward) rely on this lock, via `seconds_until_unlock`, as their fast
    path; without it they'd still be correctly refused by the budget check, but every one of
    them would cost an extra Redis round trip instead of short-circuiting immediately."""
    lockout, redis = await _lockout()

    for _ in range(MAX_ATTEMPTS):
        await lockout.reserve_attempt(EMAIL)

    assert await lockout.seconds_until_unlock(EMAIL) is not None
    assert await redis.ttl(lockout._lock_key(EMAIL)) > 0


# ---- Free lockout extension via a lockstep-TTL gap (security review, 2026-10-05) ----


async def test_fail_key_and_lock_key_always_expire_at_the_same_instant() -> None:
    """`fail_key`'s TTL is armed once, at the FIRST failure; `lock_key`'s is armed later, at
    the `max_attempts`-th. Without forcing them into lockstep, `lock_key` always expires
    first, leaving a gap where a single ordinary (non-concurrent) request sees "not locked"
    yet still finds `fail_key` alive and over budget -- re-arming the lock for a fresh full
    window at the cost of one Redis round trip, repeatable for as long as an attacker keeps
    timing one extra request into that gap. Spreading the failures across real elapsed time
    (via a controlled clock, since fakeredis's TTL math reads `time.time()` fresh on every
    command -- confirmed in `fakeredis/_basefakesocket.py`) reproduces the exact gap a purely
    sequential, zero-elapsed-time test would hide."""
    lockout, redis = await _lockout()
    clock = [1_000_000.0]

    with patch("time.time", side_effect=lambda: clock[0]):
        for _ in range(MAX_ATTEMPTS):
            await lockout.reserve_attempt(EMAIL)
            clock[0] += LOCKOUT_SECONDS / (MAX_ATTEMPTS * 5)  # spread across the window

        fail_ttl = await redis.ttl(lockout._fail_key(EMAIL))
        lock_ttl = await redis.ttl(lockout._lock_key(EMAIL))
        assert fail_ttl == lock_ttl, "both keys must expire at the same instant"

        # Advance just past that shared expiry.
        clock[0] += lock_ttl + 1
        assert await redis.ttl(lockout._lock_key(EMAIL)) == -2
        assert await redis.ttl(lockout._fail_key(EMAIL)) == -2, (
            "fail_key must be gone too -- a surviving, over-budget fail_key is exactly the "
            "gap a single ordinary request could exploit to re-arm the lock for free"
        )

        # One more ordinary request must start a genuinely fresh count, not resurrect a lock.
        attempts = await lockout.reserve_attempt(EMAIL)
        assert attempts == 1
        assert await redis.ttl(lockout._lock_key(EMAIL)) == -2


# ---- Crash-proof TTL repair (QA review, 2026-10-05) ----


async def test_a_counter_left_without_ttl_is_repaired_by_the_next_attempt() -> None:
    """Forces the exact state a crash between INCR and EXPIRE would leave: a failure
    counter with no TTL. The next reserved attempt must arm the TTL, not skip it because
    attempts is no longer 1 -- this is the case the pre-fix `if attempts == 1: expire(...)`
    missed."""
    lockout, redis = await _lockout()

    # Simulate the crash: an INCR happened, but its EXPIRE never ran.
    await redis.incr(lockout._fail_key(EMAIL))
    assert await redis.ttl(lockout._fail_key(EMAIL)) == -1  # no TTL, would never clear

    await lockout.reserve_attempt(EMAIL)

    ttl = await redis.ttl(lockout._fail_key(EMAIL))
    assert ttl > 0, "the counter must carry a TTL after any reserve_attempt call"


async def test_ttl_is_repaired_even_when_the_crash_happened_several_attempts_in() -> None:
    """The pre-fix code only ever armed the TTL on the call that saw attempts == 1, so a key
    left without one several attempts into the climb -- not just on the very first attempt --
    would stay TTL-less until the counter happened to reset. `EXPIRE ... NX` must run on every
    attempt, not only the first, for this to self-heal regardless of where the crash lands."""
    lockout, redis = await _lockout()
    fail_key = lockout._fail_key(EMAIL)

    # Three raw increments with no EXPIRE at all, as repeated crashes would leave it.
    for _ in range(3):
        await redis.incr(fail_key)
    assert await redis.ttl(fail_key) == -1

    await lockout.reserve_attempt(EMAIL)  # attempts becomes 4, still below MAX_ATTEMPTS

    assert await redis.ttl(fail_key) > 0


async def test_undo_reservation_gives_back_only_its_own_slot() -> None:
    """QA/security review (2026-10-05): `undo_reservation` (used by `login()`'s
    inactive-account branch) must decrement, not wipe -- an attacker's own, independently
    accumulating reservations for the same email must survive a legitimate-but-inactive
    user's correct-password attempt landing in between. Using `reset` here instead would
    erase them, handing the attacker a fresh full budget for free every time the real
    owner retries."""
    lockout, redis = await _lockout()

    for _ in range(3):  # three attacker guesses already reserved
        await lockout.reserve_attempt(EMAIL)
    await lockout.reserve_attempt(EMAIL)  # the inactive owner's own request reserves a 4th

    await lockout.undo_reservation(EMAIL)  # only that 4th slot is given back

    assert await redis.get(lockout._fail_key(EMAIL)) == "3"


async def test_reset_after_repaired_ttl_clears_the_counter() -> None:
    """Sanity check, not a differentiator for either fix (`reset` is a plain DELETE,
    untouched by both): a successful login must still clear a counter whose TTL was
    repaired by the fix above."""
    lockout, redis = await _lockout()
    await redis.incr(lockout._fail_key(EMAIL))  # pre-existing, TTL-less counter
    await lockout.reserve_attempt(EMAIL)

    await lockout.reset(EMAIL)

    assert await redis.get(lockout._fail_key(EMAIL)) is None


# ---- login() actually wires the budget check to skip verification (QA review, 2026-10-05) ----

LOGIN_EMAIL = "login-budget@example.com"
LOGIN_PASSWORD = "StrongPass1"


async def test_login_skips_password_verification_once_the_budget_is_already_spent(
    db_session_factory: async_sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The unit tests above prove `reserve_attempt`'s own return values; this proves
    `auth_service.login` actually ACTS on them. Seeds `fail_key` directly to one past
    budget WITHOUT setting `lock_key`, so the only thing that can reject this call is the
    new `attempts > lockout.max_attempts` check in `login()` itself (`seconds_until_unlock`'s
    pre-existing fast path is deliberately not armed here) -- a regression that deleted that
    check but left everything else intact would make this test call `verify_password` and
    succeed, which the spy below would catch."""
    redis = FakeAsyncRedis(decode_responses=True)
    async with db_session_factory() as session:
        await auth_service.register_organization(
            session,
            organization_name="Budget Co",
            full_name="Budget Owner",
            email=LOGIN_EMAIL,
            password=LOGIN_PASSWORD,
            plan=Plan.STARTER,
        )

        fail_key = f"login:fail:{LOGIN_EMAIL}"
        for _ in range(6):  # one past MAX_ATTEMPTS, lock_key deliberately left unset
            await redis.incr(fail_key)

        verify_password_called = False
        original_verify_password = security.verify_password

        def _spy_verify_password(*args: object, **kwargs: object) -> bool:
            nonlocal verify_password_called
            verify_password_called = True
            return original_verify_password(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(security, "verify_password", _spy_verify_password)

        with pytest.raises(AccountLockedError):
            await auth_service.login(
                session,
                redis,
                email=LOGIN_EMAIL,
                password=LOGIN_PASSWORD,  # the CORRECT password
                ip=None,
                user_agent=None,
            )

        assert not verify_password_called, (
            "a request already over budget must be refused before verification -- if this "
            "fired, the correct password would have been checked and login would have "
            "succeeded instead of raising"
        )
