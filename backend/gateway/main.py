from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from backend.gateway.routes import proxy_routes
from backend.services.auth.config.firebase import init_firebase
from dotenv import load_dotenv, find_dotenv
import os
import uvicorn
from rich import print as rprint
from backend.gateway.middlewares.rate_limiter import RateLimitMiddleware
from backend.shared.redis_client import get_redis, close_redis 
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gateway startup/shutdown."""
    init_firebase()
    await get_redis() 
    rprint("✅ Gateway Ready")
    yield
    await close_redis()
    rprint("🛑 Gateway Shutting Down")

app = FastAPI(
    lifespan=lifespan,
    title="KBC API Gateway",
    description="Central entry point for Unity client"
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# Custom conditional Firebase auth middleware
@app.middleware("http")
async def conditional_firebase_auth(request: Request, call_next):
    """
    Apply Firebase auth selectively based on the endpoint.
    """
    path = request.url.path
    method = request.method
    
    logger.info(f"🔄 Middleware called: {method} {path}")
    
    # List of paths that DON'T need Firebase auth
    skip_auth_paths = [
        "/",
        "/health",
        "/health/redis",
        "/favicon.ico",
    ]
    
    skip_auth_prefixes = [
        "/auth/",
        "/game/multiplayer/ws/",
    ]
    
    # Check if we should skip auth
    should_skip = (
        path in skip_auth_paths or
        any(path.startswith(prefix) for prefix in skip_auth_prefixes)
    )
    
    if should_skip:
        logger.info(f"🔓 SKIPPING Firebase auth for: {path}")
        rprint(f"[green]🔓 SKIPPING auth: {method} {path}[/green]")
        return await call_next(request)
    
    # For all other routes, verify Firebase token
    logger.info(f"🔐 REQUIRING Firebase auth for: {path}")
    rprint(f"[yellow]🔐 REQUIRING auth: {method} {path}[/yellow]")
    
    from firebase_admin import auth as firebase_auth
    
    auth_header = request.headers.get("Authorization")
    logger.info(f"📋 Auth header present: {bool(auth_header)}")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.error(f"❌ Missing/invalid Authorization header for {path}")
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.split("Bearer ")[1]
    
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        firebase_uid = decoded_token.get("uid")
        
        request.state.firebase_uid = firebase_uid
        request.state.firebase_email = decoded_token.get("email")
        
        logger.info(f"✅ Token verified for user: {firebase_uid[:8]}...")
        
    except Exception as e:
        logger.error(f"❌ Token verification failed: {str(e)}")
        raise HTTPException(status_code=403, detail=f"Invalid Firebase token: {str(e)}")
    
    return await call_next(request)

# Register proxy routes
app.include_router(proxy_routes.router)

@app.get("/")
async def gateway_root():
    return {
        "status": "API Gateway Running",
        "routes": {
            "/auth/* → Auth Service (port 8001)",
            "/game/* → Game Service (port 8002)",
            "/game/multiplayer/ws/{player_id} → WebSocket (no auth)"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/health/redis")
async def redis_health():
    redis_client = await get_redis()
    is_healthy = await redis_client.ping()
    return {
        "redis": "healthy" if is_healthy else "unhealthy",
        "ping": is_healthy
    }

if __name__ == "__main__":
    port = int(os.getenv("GATEWAY_PORT", 8000))
    uvicorn.run("backend.gateway.main:app", host="0.0.0.0", port=port, reload=True, log_level="info")
