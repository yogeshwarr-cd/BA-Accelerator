import redis.asyncio as aioredis
from backend.config import settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class RedisClient:
    """
    Asynchronous Redis Client interface.
    """
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client = aioredis.from_url(self.redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire_seconds: Optional[int] = None) -> None:
        await self.client.set(key, value, ex=expire_seconds)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    async def close(self) -> None:
        await self.client.aclose()

# Optional type hinting import
from typing import Optional

# Global singleton client instance
redis_client = RedisClient()

# INTEGRATION NOTE
# This module exposes a global `redis_client` instance.
# Member 1 (ingestion/fingerprint.py) relies on this to execute SHA256 duplicate verification lookup.
