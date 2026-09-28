"""Token state in Redis: valid refresh tokens (rotation) and revoked access tokens.

Keeps a user → active-refresh-jtis index to allow bulk revocation (password change/
recovery, account deactivation) — MED-001.
"""

import redis.asyncio as aioredis


class TokenStore:
    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    @staticmethod
    def _refresh_key(jti: str) -> str:
        return f"auth:refresh:{jti}"

    @staticmethod
    def _user_index_key(user_id: str) -> str:
        return f"auth:user-refresh:{user_id}"

    async def store_refresh(self, jti: str, user_id: str, ttl_seconds: int) -> None:
        index_key = self._user_index_key(user_id)
        pipe = self._redis.pipeline()
        pipe.set(self._refresh_key(jti), user_id, ex=ttl_seconds)
        pipe.sadd(index_key, jti)
        # The index lives as long as the newest refresh token
        pipe.expire(index_key, ttl_seconds)
        await pipe.execute()

    async def consume_refresh(self, jti: str) -> str | None:
        """Returns the user_id and atomically invalidates the jti (single-use rotation)."""
        user_id = await self._redis.getdel(self._refresh_key(jti))
        if user_id is not None:
            await self._redis.srem(self._user_index_key(user_id), jti)
        return user_id

    async def revoke_refresh(self, jti: str) -> None:
        await self.consume_refresh(jti)

    async def revoke_all_refresh_for_user(self, user_id: str) -> None:
        index_key = self._user_index_key(user_id)
        jtis = await self._redis.smembers(index_key)
        pipe = self._redis.pipeline()
        for jti in jtis:
            pipe.delete(self._refresh_key(jti))
        pipe.delete(index_key)
        await pipe.execute()

    async def block_access(self, jti: str, ttl_seconds: int) -> None:
        await self._redis.set(f"auth:block:{jti}", "1", ex=max(ttl_seconds, 1))

    async def is_access_blocked(self, jti: str) -> bool:
        return await self._redis.exists(f"auth:block:{jti}") == 1
