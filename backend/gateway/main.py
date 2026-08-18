from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.gateway.routes import proxy_routes
from backend.gateway.middlewares.middleware import FirebaseAuthMiddleware
from backend.services.auth.config.firebase import init_firebase  # ← Gateway needs Firebase too!
from dotenv import load_dotenv, find_dotenv
import os
import sys
import uvicorn

load_dotenv(find_dotenv())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gateway startup/shutdown.
    
    Gateway needs Firebase SDK to verify tokens in middleware.
    """
    init_firebase()
    print("✅ Gateway Ready")
    yield
    print("🛑 Gateway Shutting Down")

app = FastAPI(
    lifespan=lifespan,
    title="KBC API Gateway",
    description="Central entry point for Unity client"
)

# Add Firebase authentication middleware
# This runs BEFORE routes - validates tokens first
app.add_middleware(FirebaseAuthMiddleware)

# Register proxy routes
app.include_router(proxy_routes.router)

@app.get("/")
async def gateway_root():
    return {
        "status": "API Gateway Running",
        "routes": {
            "/auth/* → Auth Service (port 8001)",
            "/game/* → Game Service (port 8002)"
        }
    }

@app.get("/health")
async def health_check():
    """Public endpoint for monitoring"""
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.getenv("GATEWAY_PORT", 8000))
    uvicorn.run("backend.gateway.main:app", host="0.0.0.0", port=port, reload=True)
