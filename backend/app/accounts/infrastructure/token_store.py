"""Estado de tokens no Redis: refresh válidos (rotação) e access revogados."""

import redis.asyncio as aioredis


class TokenStore:
    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def store_refresh(self, jti: str, user_id: str, ttl_seconds: int) -> None:
        await self._redis.set(f"auth:refresh:{jti}", user_id, ex=ttl_seconds)

    async def consume_refresh(self, jti: str) -> str | None:
        """Retorna o user_id e invalida o jti atomicamente (rotação single-use)."""
        return await self._redis.getdel(f"auth:refresh:{jti}")

    async def revoke_refresh(self, jti: str) -> None:
        await self._redis.delete(f"auth:refresh:{jti}")

    async def block_access(self, jti: str, ttl_seconds: int) -> None:
        await self._redis.set(f"auth:block:{jti}", "1", ex=max(ttl_seconds, 1))

    async def is_access_blocked(self, jti: str) -> bool:
        return await self._redis.exists(f"auth:block:{jti}") == 1
