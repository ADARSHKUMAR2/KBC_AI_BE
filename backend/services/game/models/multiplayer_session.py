from beanie import Document
from pydantic import Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

from backend.services.game.models.expert import Expert


class MultiplayerStatus(str, Enum):
    """Multiplayer game lifecycle states"""
    WAITING = "waiting"           # Waiting for second player
    READY = "ready"               # Both players connected
    IN_PROGRESS = "in_progress"   # Game actively running
    COMPLETED = "completed"       # Game finished
    ABANDONED = "abandoned"       # A player disconnected


class PlayerState(str, Enum):
    """Individual player connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ANSWERED = "answered"         # Submitted answer for current question


class MultiplayerGameSession(Document):
    """
    Represents a real-time multiplayer game between 2 players.
    
    Key Differences from GameSession:
    - Tracks TWO players with separate scores
    - Server-driven timer (both see same countdown)
    - WebSocket-based real-time synchronization
    - Redis Pub/Sub for cross-instance messaging
    """
    
    # ── Players ─────────────────────────────────────────
    player1_id: str = Field(..., index=True)  # Firebase UID
    player2_id: Optional[str] = None          # Firebase UID (None until matched)
    
    player1_socket_id: Optional[str] = None   # WebSocket connection ID
    player2_socket_id: Optional[str] = None
    
    player1_status: PlayerState = Field(default=PlayerState.CONNECTED)
    player2_status: PlayerState = Field(default=PlayerState.DISCONNECTED)
    
    # ── Game State ──────────────────────────────────────
    question_ids: List[str] = Field(default_factory=list)  # 10 questions
    current_question_index: int = Field(default=0)
    
    # Scores for each player
    player1_score: int = Field(default=0)
    player2_score: int = Field(default=0)
    
    # Answers submitted (index = question number, value = option index 0-3)
    player1_answers: List[Optional[int]] = Field(default_factory=list)
    player2_answers: List[Optional[int]] = Field(default_factory=list)
    
    # ── Experts & Saboteur ──────────────────────────────
    assigned_experts: List[Expert] = Field(default_factory=list)
    saboteur_expert_name: Optional[str] = None
    
    # ── Timing ──────────────────────────────────────────
    question_start_time: Optional[datetime] = None  # When current question started
    time_per_question: int = Field(default=30)      # Seconds per question
    
    # ── Status ──────────────────────────────────────────
    session_status: MultiplayerStatus = Field(default=MultiplayerStatus.WAITING)
    total_questions: int = Field(default=10)
    
    # ── Timestamps ──────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None      # When player2 joined
    completed_at: Optional[datetime] = None
    
    class Settings:
        name = "multiplayer_sessions"
    
    # ── Helper Methods ──────────────────────────────────
    
    def is_complete(self) -> bool:
        """Check if all questions answered"""
        return self.current_question_index >= self.total_questions
    
    def get_current_question_id(self) -> Optional[str]:
        """Get current question ID"""
        if self.is_complete() or self.current_question_index < 0:
            return None
        return self.question_ids[self.current_question_index]
    
    def both_players_answered(self) -> bool:
        """Check if both players submitted answers for current question"""
        return (
            self.player1_status == PlayerState.ANSWERED and
            self.player2_status == PlayerState.ANSWERED
        )
    
    def advance_question(self):
        """Move to next question and reset player states"""
        self.current_question_index += 1
        self.player1_status = PlayerState.CONNECTED
        self.player2_status = PlayerState.CONNECTED
        self.question_start_time = datetime.utcnow()
        
        if self.is_complete():
            self.session_status = MultiplayerStatus.COMPLETED
            self.completed_at = datetime.utcnow()
    
    def get_winner(self) -> Optional[str]:
        """Determine winner. Returns 'player1', 'player2', or 'tie'"""
        if not self.is_complete():
            return None
        
        if self.player1_score > self.player2_score:
            return "player1"
        elif self.player2_score > self.player1_score:
            return "player2"
        else:
            return "tie"
