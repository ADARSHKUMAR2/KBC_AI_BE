import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# Import database initialization
from backend.shared.database import get_database

# Import all models that need to be registered with Beanie
from backend.services.game.models.question import Question
from backend.services.game.models.game_session import GameSession
from backend.services.auth.models.user import User

# Import routes
from backend.services.game.routes.game_routes import router as game_router
from rich import print

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Startup:
    - Initialize MongoDB connection
    - Register Beanie models (Question, GameSession)
    
    Shutdown:
    - Close database connections (handled automatically by Motor)
    """
    # ========== STARTUP ==========
    print("🎮 Game Service: Starting up...")
    
    # Initialize MongoDB with all game models
    try:
        await get_database(document_models=[Question, GameSession, User])
        print("✅ Game Service: Database initialized successfully")
    except Exception as e:
        print(f"❌ Game Service: Failed to initialize database: {e}")
        raise
    
    yield  # Application runs here
    
    # ========== SHUTDOWN ==========
    print("🎮 Game Service: Shutting down...")


# ========== FASTAPI APP ==========

app = FastAPI(
    title="KBC AI - Game Service",
    description="Manages trivia gameplay, questions, experts, and sessions",
    version="1.0.0-phase2",
    lifespan=lifespan
)

# ========== CORS MIDDLEWARE ==========

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to Unity's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== ROUTES ==========

# Include game routes (all /game/* endpoints)
app.include_router(game_router)

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint - health check for the Game Service.
    
    The Gateway can hit this to verify service is running.
    """
    return {
        "service": "game-service",
        "status": "running",
        "version": "1.0.0-phase2",
        "endpoints": {
            "health": "/game/health",
            "start_session": "POST /game/session/start",
            "get_question": "GET /game/session/{session_id}/question",
            "submit_answer": "POST /game/session/{session_id}/answer",
            "get_summary": "GET /game/session/{session_id}/summary"
        }
    }


# ========== RUN SERVER (Development Only) ==========

if __name__ == "__main__":
    """
    Run the Game Service directly (for local testing).
    
    In production:
    - This will be managed by the Gateway
    - Or run via: uvicorn backend.services.game.main:app --port 8002
    """
    port = int(os.getenv("GAME_SERVICE_PORT", 8002))
    
    print(f"\n{'='*60}")
    print(f"🎮 Starting Game Service on http://localhost:{port}")
    print(f"📚 API Docs: http://localhost:{port}/docs")
    print(f"{'='*60}\n")
    
    uvicorn.run(
        "backend.services.game.main:app",
        host="0.0.0.0",
        port=port,
        reload=True  # Auto-reload on code changes (development only)
    )
