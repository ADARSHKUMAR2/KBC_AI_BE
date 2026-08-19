import os
import json
from typing import Optional, Any
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

class RedisClient:
    """
    Async Redis client with JSON serialization helpers.
    
    Usage:
        redis_client = await get_redis()
        await redis_client.set("key", {"data": "value"}, ex=300)
        data = await redis_client.get("key")
    """
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection pool"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10
        )
        print(f"✅ Redis connected: {redis_url}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            print("🛑 Redis connection closed")
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None):
        """Set a key with optional TTL (seconds)"""
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await self.redis.set(key, serialized, ex=ex)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get and deserialize a key"""
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    async def delete(self, key: str):
        """Delete a key"""
        await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return bool(await self.redis.exists(key))
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        return await self.redis.incrby(key, amount)
    
    async def expire(self, key: str, seconds: int):
        """Set expiration on existing key"""
        await self.redis.expire(key, seconds)
    
    # ── Leaderboard (Sorted Set) ────────────────────────────────
    async def zadd(self, key: str, mapping: dict):
        """Add to sorted set. mapping = {member: score}"""
        await self.redis.zadd(key, mapping)
    
    async def zrevrange(self, key: str, start: int, end: int, withscores: bool = True):
        """Get top N from sorted set (highest scores first)"""
        return await self.redis.zrevrange(key, start, end, withscores=withscores)
    
    async def zscore(self, key: str, member: str) -> Optional[float]:
        """Get score of a member"""
        return await self.redis.zscore(key, member)
    
    async def ping(self) -> bool:
        """Health check"""
        try:
            return await self.redis.ping()
        except:
            return False


# ── Global singleton instance ───────────────────────────────────
_redis_client: Optional[RedisClient] = None

async def get_redis() -> RedisClient:
    """Get the global Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client

async def close_redis():
    """Close the global Redis client"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
