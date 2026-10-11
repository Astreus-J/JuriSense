"""Redis-backed, fixed-window rate limiting (docs/07-engineering/security.md "Rate limiting
on public endpoints", #112/#143). Mirrors `app/identity/infrastructure/lockout.py`'s exact
atomic-counter pattern (`INCR` + `EXPIRE ... NX`) -- the same reasoning applies here: `INCR`
is atomic, so a burst of concurrent requests against the same key gets strictly increasing,
gap-free counts regardless of network-level interleaving, and `EXPIRE ... NX` only arms the
window on the FIRST hit, so every later hit in the same window shares its remaining TTL.

Two call shapes, both built on the same `RateLimiter`:
- `rate_limit_by_ip` (this module): for unauthenticated routes, keyed on the caller's IP.
- `app.identity.api.deps.rate_limit_by_organization`: for authenticated routes, keyed on the
  caller's `organization_id` -- lives in `identity` (not here) because it depends on
  `CurrentUser`, and `app/core` must not depend on any bounded context.
"""

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

from app.core.redis import RedisDep


class RateLimitExceededError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds


class RateLimiter:
    def __init__(self, redis: Redis, *, max_requests: int, window_seconds: int) -> None:
        self._redis = redis
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def hit(self, key: str) -> None:
        """Raises `RateLimitExceededError` once `key` has been hit more than `max_requests`
        times within the current window. The window starts at this key's FIRST hit (not a
        clock-aligned bucket), so a key that goes quiet for `window_seconds` always gets a
        fresh budget on its next hit, same as `LoginLockout`'s own counter."""
        count = await self._redis.incr(key)
        await self._redis.expire(key, self._window_seconds, nx=True)
        if count > self._max_requests:
            ttl = await self._redis.ttl(key)
            retry_after = ttl if ttl > 0 else self._window_seconds
            raise RateLimitExceededError(retry_after_seconds=retry_after)


def _too_many_requests(exc: RateLimitExceededError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Try again later.",
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


def rate_limit_by_ip(*, max_requests: int, window_seconds: int, key_prefix: str):
    """FastAPI dependency factory for an UNAUTHENTICATED route: keys on the caller's IP
    address, read from `request.client.host`. This dependency trusts whatever `request.
    client.host` says and does not parse `X-Forwarded-For`/`Forwarded`/`CF-Connecting-IP`
    itself -- Starlette only populates `request.client` from forwarded headers when uvicorn
    is run with `--proxy-headers` AND a `--forwarded-allow-ips` that actually lists the
    immediate upstream (the Nginx reverse proxy), neither of which exists in this codebase
    yet (security review, 2026-10-11): no `nginx` service in `docker-compose.yml`, no
    `ProxyHeadersMiddleware`, no uvicorn flag in `backend/Dockerfile`. Configuring that whole
    chain is tracked as its own epic (#150-#153, "Reverse proxy (Nginx) & HTTPS" /
    "Configure and verify proxy headers / trusted-proxy handling") -- deliberately NOT done
    piecemeal here, since Nginx's own config and the uvicorn trust setting have to agree
    with each other to be safe (trusting a forwarded header from an untrusted hop lets an
    attacker spoof any IP they like, defeating this limiter entirely).

    Until #153 lands, `request.client.host` resolves to whatever TCP peer connects directly
    to this process -- in production, that's Nginx's own address (or, with no Nginx yet, a
    Cloudflare edge IP), not the real visitor's. Every distinct visitor collapses onto the
    same handful of keys, so this limiter is effectively a single shared, GLOBAL budget in
    production right now, not a per-visitor one -- strictly better than the previous
    completely-unthrottled state, but not yet the per-visitor granularity #112 describes.
    No code change is needed here once #153 lands: Starlette/uvicorn populate `request.
    client.host` correctly on their own at that point, transparently to this function.

    Runs before the route body (an ordinary FastAPI dependency), so an over-limit caller
    never reaches the route's own logic -- same enforcement-order guarantee `require_
    permission` gives RBAC (`docs/04-architecture/security-architecture.md` §2)."""

    async def _check(request: Request, redis: RedisDep) -> None:
        client_host = request.client.host if request.client else "unknown"
        limiter = RateLimiter(redis, max_requests=max_requests, window_seconds=window_seconds)
        try:
            await limiter.hit(f"{key_prefix}:{client_host}")
        except RateLimitExceededError as exc:
            raise _too_many_requests(exc) from exc

    return _check
