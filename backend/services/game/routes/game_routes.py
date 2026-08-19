from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel

from backend.services.game.controllers.game_controller import GameController
from backend.services.auth.models.user import User

# Create router
router = APIRouter(prefix="/game", tags=["Game"])

# Initialize controller
game_controller = GameController()


# ========== REQUEST/RESPONSE MODELS ==========

class StartSessionRequest(BaseModel):
    """
    Request body for starting a new game session.
    Unity will send this with the user's Firebase UID.
    """
    user_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "firebase_uid_abc123"
            }
        }


class SubmitAnswerRequest(BaseModel):
    """
    Request body for submitting an answer.
    Unity sends which option (0-3) the player selected.
    """
    selected_option: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "selected_option": 2
            }
        }


# ========== ENDPOINTS ==========

@router.post("/session/start", status_code=201)
async def start_game_session(request: StartSessionRequest):
    """
    Start a new game session.
    
    **Unity Flow:**
    1. User logs in and gets Firebase UID
    2. Unity calls this endpoint with user_id
    3. Backend creates session and returns first question
    4. Unity displays question and expert advice
    
    **Returns:**
    - session_id: Use this for all subsequent requests
    - question: First question data
    - expert_advice: Advice from all 3 experts
    
    **Example Response:**
    ```json
    {
        "session_id": "64f1a2b3c4d5e6f7a8b9c0d1",
        "status": "started",
        "total_questions": 10,
        "question": {
            "question_text": "What is the capital of France?",
            "options": ["Paris", "London", "Berlin", "Madrid"],
            "difficulty": "easy",
            "category": "geography"
        },
        "expert_advice": [
            {
                "expert_name": "Dr. History",
                "advice_text": "Based on historical records, I believe option 1 (Paris) is correct.",
                "confidence_percentage": 85,
                "recommended_option": 0
            },
            ...
        ],
        "current_question_number": 1
    }
    ```
    """
    try:
        result = await game_controller.start_session(user_id=request.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.get("/session/{session_id}/question")
async def get_question(session_id: str):
    """
    Get the current question for an active session.
    
    **Unity Flow:**
    1. User is in the middle of a game
    2. Unity calls this to fetch the current question
    3. Backend returns question + expert advice
    4. Unity displays them
    
    **When to use:**
    - After submit_answer returns "continue" status
    - To resume a game after refresh/reconnect
    - To fetch question details
    
    **Returns:**
    - question: Current question data
    - expert_advice: Fresh advice from all 3 experts
    - current_question_number: Where player is (e.g., "Question 3 of 10")
    - current_score: How many correct so far
    
    **Error Cases:**
    - 404: Session not found
    - 400: Session is already complete (use /summary instead)
    """
    try:
        result = await game_controller.get_current_question(session_id=session_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch question: {str(e)}")


@router.post("/session/{session_id}/answer")
async def submit_answer(session_id: str, request: SubmitAnswerRequest):
    """
    Submit the player's answer and get immediate feedback.
    
    **Unity Flow:**
    1. Player reads question and expert advice
    2. Player clicks one of the 4 option buttons
    3. Unity sends selected_option (0-3) to this endpoint
    4. Backend checks answer, updates score, advances game
    5. Unity shows "Correct!" or "Wrong!" with explanation
    6. Unity either loads next question or shows summary
    
    **Returns:**
    - is_correct: True/False
    - correct_answer: The correct option index
    - correct_option_text: The actual answer text
    - explanation: Why this is the answer
    - current_score: Updated score
    - game_status: "continue" or "completed"
    
    **If game_status is "continue":**
    - Call GET /session/{session_id}/question to fetch next question
    
    **If game_status is "completed":**
    - Call GET /session/{session_id}/summary to show final results
    
    **Example Response:**
    ```json
    {
        "session_id": "64f1a2b3c4d5e6f7a8b9c0d1",
        "is_correct": true,
        "correct_answer": 0,
        "correct_option_text": "Paris",
        "explanation": "Paris has been the capital of France since the 12th century.",
        "current_score": 3,
        "questions_answered": 3,
        "total_questions": 10,
        "game_status": "continue",
        "next_question_number": 4,
        "message": "Ready for next question"
    }
    ```
    """
    try:
        result = await game_controller.submit_answer(
            session_id=session_id,
            selected_option=request.selected_option
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit answer: {str(e)}")


@router.get("/session/{session_id}/summary")
async def get_summary(session_id: str):
    """
    Get the complete summary of a finished game session.
    
    **Unity Flow:**
    1. Game is complete (all questions answered)
    2. Unity calls this endpoint
    3. Backend returns detailed statistics
    4. Unity shows results screen:
       - Final score (e.g., "7 out of 10")
       - Accuracy percentage (e.g., "70%")
       - Which questions were correct/wrong
       - (Phase 3 will add: Traitor reveal, Coins won)
    
    **Returns:**
    - final_score: Number of correct answers
    - accuracy_percentage: Score as percentage
    - questions_breakdown: Detailed list of all questions
    - experts_used: The 3 experts who helped
    
    **Example Response:**
    ```json
    {
        "session_id": "64f1a2b3c4d5e6f7a8b9c0d1",
        "status": "completed",
        "final_score": 7,
        "total_questions": 10,
        "accuracy_percentage": 70.0,
        "questions_breakdown": [
            {
                "question_number": 1,
                "question_text": "What is the capital of France?",
                "user_answer": "Paris",
                "correct_answer": "Paris",
                "was_correct": true,
                "category": "geography"
            },
            ...
        ],
        "experts_used": [
            {
                "name": "Dr. History",
                "personality": "Historian"
            },
            {
                "name": "Risk Taker",
                "personality": "Risky"
            },
            {
                "name": "The Skeptic",
                "personality": "Skeptical"
            }
        ],
        "started_at": "2024-01-15T10:30:00",
        "completed_at": "2024-01-15T10:45:00"
    }
    ```
    """
    try:
        result = await game_controller.get_session_summary(session_id=session_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {str(e)}")

@router.get("/leaderboard")
async def get_leaderboard():
    """
    Get top 10 players by total score across ALL games played.
    Queries MongoDB directly to ensure permanent accuracy.
    """
    
    top_users = await User.find().sort(-User.total_score).limit(10).to_list()
    
    leaderboard = []
    for i, user in enumerate(top_users):
        leaderboard.append({
            "rank": i + 1,
            "user_id": user.firebase_uid,
            "display_name": user.display_name or "Anonymous",
            "total_score": user.total_score
        })
    
    return {
        "leaderboard": leaderboard,
        "total_entries": len(leaderboard)
    }

# ========== HEALTH CHECK ==========

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint to verify Game Service is running.
    
    The Gateway can call this to ensure the service is up.
    Unity can also use this during initialization.
    """
    return {
        "status": "healthy",
        "service": "game-service",
        "version": "1.0.0-phase2"
    }

