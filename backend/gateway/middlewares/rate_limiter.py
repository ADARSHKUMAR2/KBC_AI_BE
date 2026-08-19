from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.shared.redis_client import get_redis

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit by Firebase UID: 100 requests/minute.
    Uses Redis INCR with 60-second TTL.
    """
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for public paths
        public_paths = ["/", "/health", "/auth/verify"]
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Get Firebase UID from request.state (set by FirebaseAuthMiddleware)
        firebase_uid = getattr(request.state, "firebase_uid", None)
        if not firebase_uid:
            # If no UID (auth middleware will handle this), pass through
            return await call_next(request)
        
        # Redis key: rate_limit:uid:<firebase_uid>
        redis_client = await get_redis()
        rate_key = f"rate_limit:uid:{firebase_uid}"
        
        # Increment counter
        current_count = await redis_client.incr(rate_key)
        
        # Set TTL on first request in this window
        if current_count == 1:
            await redis_client.expire(rate_key, self.window_seconds)
        
        # Check limit
        if current_count > self.max_requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds."
                }
            )
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.max_requests - current_count))
        
        return response
