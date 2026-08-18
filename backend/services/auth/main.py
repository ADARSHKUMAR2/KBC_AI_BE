from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.services.auth.config.db import init_auth_db
import uvicorn
from dotenv import load_dotenv, find_dotenv
import os
import sys
from backend.services.auth.config.firebase import init_firebase  
from backend.services.auth.routes import auth_routes
load_dotenv(find_dotenv())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown logic.
    
    On startup:
    1. Initialize Firebase Admin SDK
    2. Connect to MongoDB
    3. Initialize Beanie with User model
    """
    # Initialize Firebase first
    init_firebase()
    
    # Then initialize MongoDB
    await init_auth_db()
    
    print("✅ Auth Service Ready")
    yield
    
    # Shutdown logic (cleanup connections, etc.)
    print("🛑 Auth Service Shutting Down")

app = FastAPI(lifespan=lifespan, title="KBC Auth Service")

# Register routes
app.include_router(auth_routes.router)

@app.get("/")
async def auth_root():
    return {
        "status": "Auth Service Running",
        "endpoints": [
            "POST /auth/verify - Verify Firebase token",
            "GET /auth/profile - Get user profile"
        ]
    }


if __name__ == "__main__":
    # Run the server on port 8001 with auto-reload enabled
    port = int(os.getenv("AUTH_SERVICE_PORT", 8001))
    uvicorn.run("backend.services.auth.main:app", host="0.0.0.0", port=port, reload=True)