from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from pydantic import BaseModel

from backend.services.game.controllers.game_controller import GameController
from backend.services.auth.models.user import User
from fastapi.responses import StreamingResponse
from backend.shared.llm_client import generate_expert_advice_streaming

from backend.services.game.models.game_session import GameSession  
from backend.services.game.models.question import Question  
from backend.services.game.data.graph import run_question_generation

from fastapi import WebSocket, WebSocketDisconnect
from backend.services.game.controllers.matchmaking import matchmaking_queue
from backend.services.game.controllers.websocket_manager import connection_manager
from backend.services.game.models.multiplayer_session import MultiplayerGameSession, PlayerState, MultiplayerStatus
import asyncio


from beanie import PydanticObjectId

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
    category: Optional[str] = None 
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "firebase_uid_abc123",
                "category": "current_events"
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
        result = await game_controller.start_session(
            user_id=request.user_id,
            category=request.category
            )
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

async def get_current_user(firebase_uid: str = Header(..., alias="X-Firebase-UID")) -> str:
    """
    Extract Firebase UID from request headers.
    The Gateway should inject this after validating the JWT token.
    """
    if not firebase_uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    return firebase_uid

@router.get("/session/{session_id}/question/stream/{expert_name}")
async def stream_expert_advice(
    session_id: str,
    expert_name: str,
    firebase_uid: str = Depends(get_current_user)
):
    """
    Stream a single expert's advice token-by-token for typewriter effect.
    Unity can call this for each expert separately.
    """
    session = await GameSession.get(PydanticObjectId(session_id))
    if not session or session.firebase_uid != firebase_uid:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Find the expert
    expert = next((e for e in session.assigned_experts if e.name == expert_name), None)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    
    # Get current question
    current_q = session.questions[session.current_question_index]
    question = await Question.get(current_q.question_id)
    
    # Stream the response
    is_sab = (expert.name == session.saboteur_expert_name)
    async def event_generator():
        async for chunk in generate_expert_advice_streaming(
            expert_type=expert.personality_type.lower(),
            question_text=question.question_text,
            options=question.options,
            correct_answer=question.options[question.correct_answer],
            is_saboteur=is_sab
        ):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/generate-question", status_code=202)
async def generate_news_question():
    """
    [Phase 5] Trigger the LangGraph pipeline to generate a new
    real-time news trivia question immediately.

    Unity Flow:
    1. Player taps "Daily News" category
    2. If no current_events questions exist today, Unity calls this
    3. Backend runs the Research → Writer → Validator → Saver pipeline
    4. Returns the newly generated question

    Status 202 = "Accepted" (pipeline runs async, may take 5-15 seconds)
    """
    try:
        result = await run_question_generation()

        if result["success"]:
            return {
                "status":        "generated",
                "question_id":   result["question_id"],
                "question_text": result["question_text"],
                "message":       "New current events question generated and saved successfully!"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline failed: {result['error']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Question generation failed: {str(e)}"
        )


@router.get("/questions/current-events")
async def get_current_events_questions(limit: int = 20):
    """
    [Phase 5] Get all 'current_events' category questions from MongoDB.

    Unity Flow:
    1. Player opens the Daily News category panel
    2. Unity calls this endpoint to get available questions
    3. Display them with a 🔴 LIVE badge

    Args:
        limit: Max number of questions to return (default 20, max 50)

    Returns:
        List of questions with their metadata (no correct_answer exposed!)
    """
    limit = min(limit, 50)  # Safety cap

    questions = await Question.find(
        Question.category == "current_events"
    ).sort(-Question.created_at).limit(limit).to_list()

    question_list = []
    for q in questions:
        question_list.append({
            "question_id":   str(q.id),
            "question_text": q.question_text,
            "options":       q.options,
            "difficulty":    q.difficulty,
            "category":      q.category,
            "created_at":    q.created_at.isoformat(),
            # NOTE: correct_answer is NOT included here for security
            # Unity gets it only after submitting through the game session
        })

    return {
        "questions":    question_list,
        "total":        len(question_list),
        "category":     "current_events",
        "last_updated": question_list[0]["created_at"] if question_list else None
    }


    # ========== MULTIPLAYER WEBSOCKET ENDPOINTS ==========

@router.websocket("/multiplayer/ws/{player_id}")
async def multiplayer_websocket(websocket: WebSocket, player_id: str):
    """
    WebSocket endpoint for real-time multiplayer.
    
    Unity Flow:
    1. User clicks "Find Match"
    2. Unity opens WebSocket connection to this endpoint
    3. Server adds player to matchmaking queue
    4. When matched, server sends "match_found" event
    5. Game proceeds with real-time synchronization
    
    Message Types (Server → Client):
    - `waiting_for_opponent`: In matchmaking queue
    - `match_found`: Opponent found, game starting
    - `question_start`: New question loaded
    - `opponent_answered`: Other player submitted answer
    - `question_end`: Both answered or timeout, show results
    - `game_over`: All questions complete, show winner
    
    Message Types (Client → Server):
    - `find_match`: Join matchmaking queue
    - `submit_answer`: Submit answer for current question
    - `cancel_matchmaking`: Leave queue
    """
    
    await connection_manager.connect(player_id, websocket)
    session_id = None
    
    try:
        while True:
            # Receive message from Unity
            data = await websocket.receive_json()
            action = data.get("action")
            
            # ── MATCHMAKING ──────────────────────────────────────
            if action == "find_match":
                socket_id = data.get("socket_id", player_id)
                session_id = await matchmaking_queue.join_queue(player_id, socket_id)
                
                if session_id:
                    # Match found immediately!
                    session = await MultiplayerGameSession.get(session_id)
                    connection_manager.register_session(
                        session_id,
                        session.player1_id,
                        session.player2_id
                    )
                    
                    # Get first question
                    first_q_id = session.question_ids[0]
                    question = await Question.get(PydanticObjectId(first_q_id))
                    
                    await connection_manager.broadcast_to_session(session_id, {
                        "type": "match_found",
                        "session_id": session_id,
                        "opponent_id": session.player2_id if player_id == session.player1_id else session.player1_id,
                        "question": {
                            "question_text": question.question_text,
                            "options": question.options,
                            "difficulty": question.difficulty,
                            "category": question.category
                        },
                        "time_limit": session.time_per_question,
                        "current_question": 1,
                        "total_questions": session.total_questions
                    })
                else:
                    # Still waiting
                    await websocket.send_json({
                        "type": "waiting_for_opponent",
                        "message": "Searching for opponent..."
                    })
            
            # ── SUBMIT ANSWER ────────────────────────────────────
            elif action == "submit_answer":
                session_id = data.get("session_id")
                selected_option = data.get("selected_option")
                
                session = await MultiplayerGameSession.get(PydanticObjectId(session_id))
                if not session:
                    await websocket.send_json({"type": "error", "message": "Session not found"})
                    continue

                # Determine which player this is
                is_player1 = (player_id == session.player1_id)
                
                # Record answer
                if is_player1:
                    session.player1_answers.append(selected_option)
                    session.player1_status = PlayerState.ANSWERED
                else:
                    session.player2_answers.append(selected_option)
                    session.player2_status = PlayerState.ANSWERED
                
                await session.save()
                
                # Notify opponent
                opponent_id = session.player2_id if is_player1 else session.player1_id
                await connection_manager.send_to_player(opponent_id, {
                    "type": "opponent_answered",
                    "message": "Opponent has answered!"
                })
                
                # Check if both answered
                if session.both_players_answered():
                    # Calculate results
                    current_q_id = session.question_ids[session.current_question_index]
                    question = await Question.get(PydanticObjectId(current_q_id))
                    
                    p1_answer = session.player1_answers[-1]
                    p2_answer = session.player2_answers[-1]
                    
                    p1_correct = (p1_answer == question.correct_answer)
                    p2_correct = (p2_answer == question.correct_answer)
                    
                    if p1_correct:
                        session.player1_score += 1
                    if p2_correct:
                        session.player2_score += 1
                    
                    # Advance to next question
                    session.advance_question()
                    await session.save()
                    
                    # Send results to both players
                    await connection_manager.send_personalized(
                        session_id,
                        player1_message={
                            "type": "question_end",
                            "your_answer_correct": p1_correct,
                            "opponent_answer_correct": p2_correct,
                            "correct_answer": question.correct_answer,
                            "explanation": question.explanation,
                            "your_score": session.player1_score,
                            "opponent_score": session.player2_score
                        },
                        player2_message={
                            "type": "question_end",
                            "your_answer_correct": p2_correct,
                            "opponent_answer_correct": p1_correct,
                            "correct_answer": question.correct_answer,
                            "explanation": question.explanation,
                            "your_score": session.player2_score,
                            "opponent_score": session.player1_score
                        }
                    )
                    
                    # Wait 3 seconds, then send next question or game over
                    await asyncio.sleep(3)
                    
                    if session.is_complete():
                        # Game over!
                        winner = session.get_winner()
                        
                        await connection_manager.send_personalized(
                            session_id,
                            player1_message={
                                "type": "game_over",
                                "result": "win" if winner == "player1" else ("tie" if winner == "tie" else "loss"),
                                "final_score": session.player1_score,
                                "opponent_score": session.player2_score,
                                "saboteur_reveal": session.saboteur_expert_name
                            },
                            player2_message={
                                "type": "game_over",
                                "result": "win" if winner == "player2" else ("tie" if winner == "tie" else "loss"),
                                "final_score": session.player2_score,
                                "opponent_score": session.player1_score,
                                "saboteur_reveal": session.saboteur_expert_name
                            }
                        )
                    else:
                        # Next question
                        next_q_id = session.question_ids[session.current_question_index]
                        next_question = await Question.get(PydanticObjectId(next_q_id))
                        
                        await connection_manager.broadcast_to_session(session_id, {
                            "type": "question_start",
                            "question": {
                                "question_text": next_question.question_text,
                                "options": next_question.options,
                                "difficulty": next_question.difficulty,
                                "category": next_question.category
                            },
                            "current_question": session.current_question_index + 1,
                            "time_limit": session.time_per_question
                        })
            
            # ── CANCEL MATCHMAKING ───────────────────────────────
            elif action == "cancel_matchmaking":
                await matchmaking_queue.leave_queue(player_id)
                await websocket.send_json({
                    "type": "matchmaking_cancelled",
                    "message": "Removed from queue"
                })
    
    except WebSocketDisconnect:
        connection_manager.disconnect(player_id)
        
        # Handle mid-game disconnect
        if session_id:
            session = await MultiplayerGameSession.get(PydanticObjectId(session_id))
            if session and session.session_status == MultiplayerStatus.IN_PROGRESS:
                # Notify opponent
                opponent_id = session.player2_id if player_id == session.player1_id else session.player1_id
                await connection_manager.send_to_player(opponent_id, {
                    "type": "opponent_disconnected",
                    "message": "Opponent left the game. You win by default!"
                })
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

