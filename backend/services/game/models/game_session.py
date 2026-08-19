from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

# Import the Expert model we just created
from backend.services.game.models.expert import Expert


class SessionStatus(str, Enum):
    """
    Enum for tracking the game session lifecycle.
    Using an Enum prevents typos and makes the code more maintainable.
    """
    ACTIVE = "active"        # Game is currently being played
    COMPLETED = "completed"  # Player finished all questions
    ABANDONED = "abandoned"  # Player left mid-game (for future resume feature)


class GameSession(Document):
    """
    Represents a complete game session for a single player.
    
    This is the central model for Phase 2. It tracks:
    - Which user is playing
    - Which questions they're answering
    - Which experts are helping them
    - Their current progress and score
    
    Think of this as a "save file" for one game.
    """
    
    # Link to the user playing this game (from Firebase Auth)
    # We use firebase_uid instead of MongoDB _id to match the User model
    user_id: str = Field(..., index=True)
    
    # List of Question IDs for this session
    # Example: ["q1_id", "q2_id", ..., "q10_id"]
    # We store IDs instead of full Question objects to save space
    question_ids: List[str] = Field(default_factory=list)
    
    # Which question is the player currently on? (0-based index)
    # If current_question_index = 3, they're on the 4th question
    current_question_index: int = Field(default=0)
    
    # The three experts assigned to this game session
    # These are embedded Expert objects (not references)
    assigned_experts: List[Expert] = Field(default_factory=list)
    
    # Player's current score (correct answers count)
    score: int = Field(default=0)
    
    # Total number of questions in this session (usually 10)
    total_questions: int = Field(default=10)
    
    # Track which answers the user gave (for post-game analysis)
    # Example: [0, 2, 1, 3, ...] where each number is the option index they chose
    user_answers: List[int] = Field(default_factory=list)
    
    # Current status of the session
    session_status: SessionStatus = Field(default=SessionStatus.ACTIVE)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Settings:
        name = "game_sessions"  # MongoDB collection name
        
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "firebase_uid_abc123",
                "question_ids": ["q1", "q2", "q3", "q4", "q5"],
                "current_question_index": 2,
                "assigned_experts": [
                    {"name": "Dr. History", "personality_type": "Historian"},
                    {"name": "Risk Taker", "personality_type": "Risky"},
                    {"name": "The Skeptic", "personality_type": "Skeptical"}
                ],
                "score": 2,
                "total_questions": 5,
                "session_status": "active"
            }
        }
    
    def is_complete(self) -> bool:
        """
        Helper method to check if the game is finished.
        
        Returns True if the player has answered all questions.
        """
        return self.current_question_index >= self.total_questions
    
    def get_current_question_id(self) -> Optional[str]:
        """
        Get the ID of the question the player is currently on.
        
        Returns None if the game is complete or invalid.
        """
        if self.is_complete() or self.current_question_index < 0:
            return None
        return self.question_ids[self.current_question_index]
    
    def advance_question(self):
        """
        Move to the next question in the session.
        
        Call this after the player submits an answer.
        """
        self.current_question_index += 1
        
        # If all questions are done, mark session as completed
        if self.is_complete():
            self.session_status = SessionStatus.COMPLETED
            self.completed_at = datetime.utcnow()
