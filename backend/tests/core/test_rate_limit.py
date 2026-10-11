"""#112/#143: `RateLimiter` -- the fixed-window Redis counter backing both
`rate_limit_by_ip` (this module) and `app.identity.api.deps.rate_limit_by_organization`.
Pure unit tests against fakeredis, mirroring `tests/identity/test_lockout_concurrency.py`'s
style for the sibling `LoginLockout` counter.
"""

from unittest.mock import Mock, patch

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import HTTPException

from app.core.rate_limit import RateLimiter, RateLimitExceededError, rate_limit_by_ip


async def _limiter(max_requests: int = 3, window_seconds: int = 60) -> RateLimiter:
    redis = FakeAsyncRedis(decode_responses=True)
    return RateLimiter(redis, max_requests=max_requests, window_seconds=window_seconds)


async def test_hits_within_budget_never_raise() -> None:
    limiter = await _limiter(max_requests=3)
    for _ in range(3):
        await limiter.hit("key")


async def test_the_hit_past_budget_raises() -> None:
    limiter = await _limiter(max_requests=3)
    for _ in range(3):
        await limiter.hit("key")
    with pytest.raises(RateLimitExceededError):
        await limiter.hit("key")


async def test_retry_after_is_a_positive_number_of_seconds() -> None:
    limiter = await _limiter(max_requests=1, window_seconds=45)
    await limiter.hit("key")
    with pytest.raises(RateLimitExceededError) as exc_info:
        await limiter.hit("key")
    assert 0 < exc_info.value.retry_after_seconds <= 45


async def test_different_keys_have_independent_budgets() -> None:
    limiter = await _limiter(max_requests=1)
    await limiter.hit("key-a")
    await limiter.hit("key-b")  # a different key -- must not inherit key-a's budget
    with pytest.raises(RateLimitExceededError):
        await limiter.hit("key-a")


async def test_a_quiet_key_gets_a_fresh_budget_after_its_window_expires() -> None:
    clock = [1_000_000.0]
    with patch("time.time", side_effect=lambda: clock[0]):
        limiter = await _limiter(max_requests=1, window_seconds=10)
        await limiter.hit("key")
        with pytest.raises(RateLimitExceededError):
            await limiter.hit("key")

        clock[0] += 11  # past the window
        await limiter.hit("key")  # must not raise: a fresh window started


def _request_from(client_host: str | None) -> Mock:
    request = Mock()
    request.client = Mock(host=client_host) if client_host is not None else None
    return request


async def test_rate_limit_by_ip_gives_different_ips_independent_budgets() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    check = rate_limit_by_ip(max_requests=1, window_seconds=60, key_prefix="test")

    await check(request=_request_from("1.2.3.4"), redis=redis)
    await check(request=_request_from("5.6.7.8"), redis=redis)  # a different IP, own budget

    with pytest.raises(HTTPException) as exc_info:
        await check(request=_request_from("1.2.3.4"), redis=redis)  # the 2nd hit for 1.2.3.4
    assert exc_info.value.status_code == 429


async def test_rate_limit_by_ip_falls_back_to_a_shared_key_when_client_is_none() -> None:
    """`request.client` is `None` for some transports/test harnesses -- both such requests
    must share the same "unknown" bucket rather than crashing on `request.client.host`."""
    redis = FakeAsyncRedis(decode_responses=True)
    check = rate_limit_by_ip(max_requests=1, window_seconds=60, key_prefix="test")

    await check(request=_request_from(None), redis=redis)
    with pytest.raises(HTTPException) as exc_info:
        await check(request=_request_from(None), redis=redis)
    assert exc_info.value.status_code == 429
