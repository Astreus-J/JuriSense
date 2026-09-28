"""Login lockout after repeated failed attempts, with a Redis-backed window."""

import redis.asyncio as aioredis


class LoginLockout:
    def __init__(self, redis: aioredis.Redis, max_attempts: int, lockout_seconds: int) -> None:
        self._redis = redis
        self._max_attempts = max_attempts
        self._lockout_seconds = lockout_seconds

    def _fail_key(self, email: str) -> str:
        return f"login:fail:{email}"

    def _lock_key(self, email: str) -> str:
        return f"login:lock:{email}"

    async def seconds_until_unlock(self, email: str) -> int | None:
        ttl = await self._redis.ttl(self._lock_key(email))
        return ttl if ttl > 0 else None

    async def register_failure(self, email: str) -> None:
        fail_key = self._fail_key(email)
        attempts = await self._redis.incr(fail_key)
        if attempts == 1:
            await self._redis.expire(fail_key, self._lockout_seconds)
        if attempts >= self._max_attempts:
            await self._redis.set(self._lock_key(email), "1", ex=self._lockout_seconds)
            await self._redis.delete(fail_key)

    async def reset(self, email: str) -> None:
        await self._redis.delete(self._fail_key(email))
