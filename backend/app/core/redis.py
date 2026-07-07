from functools import lru_cache
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends

from app.core.config import get_settings


@lru_cache
def get_redis() -> aioredis.Redis:
    return aioredis.from_url(get_settings().redis_url, decode_responses=True)


RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]
