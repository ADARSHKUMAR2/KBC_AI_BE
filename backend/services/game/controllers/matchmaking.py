import asyncio
import json
from typing import Optional
from datetime import datetime
from backend.shared.redis_client import get_redis
from backend.services.game.models.multiplayer_session import (
    MultiplayerGameSession, 
    MultiplayerStatus,
    PlayerState
)
from backend.services.game.models.question import Question
from backend.services.game.models.expert import Expert
import random


class MatchmakingQueue:
    """
    Redis-backed matchmaking queue for real-time multiplayer.
    
    Flow:
    1. Player1 calls find_match() → added to Redis queue
    2. Player2 calls find_match() → matched with Player1
    3. MultiplayerGameSession created
    4. Both players notified via WebSocket
    """
    
    QUEUE_KEY = "matchmaking:queue"           # Redis list
    TIMEOUT_KEY = "matchmaking:timeout:"      # Redis string (player_id → timestamp)
    QUEUE_TIMEOUT = 60  # seconds before removing stale entries
    
    def __init__(self):
        self.redis = None
    
    async def _get_redis(self):
        """Lazy load Redis client"""
        if not self.redis:
            self.redis = await get_redis()
        return self.redis
    
    async def join_queue(self, player_id: str, socket_id: str) -> Optional[str]:
        """
        Add player to matchmaking queue.
        
        Returns:
        - None if added to queue (waiting for opponent)
        - session_id if immediately matched
        """
        redis = await self._get_redis()
        
        # Check if another player is already waiting
        waiting_player_data = await redis.redis.lpop(self.QUEUE_KEY)
        
        if waiting_player_data:
            # Match found! Create multiplayer session
            waiting_player = json.loads(waiting_player_data)
            session_id = await self._create_multiplayer_session(
                player1_id=waiting_player["player_id"],
                player1_socket_id=waiting_player["socket_id"],
                player2_id=player_id,
                player2_socket_id=socket_id
            )
            return session_id
        else:
            # No one waiting, add this player to queue
            player_data = json.dumps({
                "player_id": player_id,
                "socket_id": socket_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            await redis.redis.rpush(self.QUEUE_KEY, player_data)
            
            # Set timeout to auto-remove if no match found
            await redis.set(
                f"{self.TIMEOUT_KEY}{player_id}",
                datetime.utcnow().isoformat(),
                ex=self.QUEUE_TIMEOUT
            )
            
            return None  # Still waiting
    
    async def leave_queue(self, player_id: str):
        """Remove player from queue (e.g., they cancelled matchmaking)"""
        redis = await self._get_redis()
        
        # Get all players in queue
        queue_length = await redis.redis.llen(self.QUEUE_KEY)
        for i in range(queue_length):
            player_data = await redis.redis.lindex(self.QUEUE_KEY, i)
            if player_data:
                player = json.loads(player_data)
                if player["player_id"] == player_id:
                    # Remove from queue
                    await redis.redis.lrem(self.QUEUE_KEY, 1, player_data)
                    await redis.delete(f"{self.TIMEOUT_KEY}{player_id}")
                    return True
        return False
    
    async def _create_multiplayer_session(
        self,
        player1_id: str,
        player1_socket_id: str,
        player2_id: str,
        player2_socket_id: str
    ) -> str:
        """
        Create a new multiplayer game session.
        
        Steps:
        1. Fetch 10 random questions
        2. Assign 3 experts (one is secret Saboteur)
        3. Create MultiplayerGameSession
        4. Save to MongoDB
        """
        # Fetch random questions
        all_questions = await Question.find_all().to_list()
        if len(all_questions) < 10:
            raise ValueError("Not enough questions in database for multiplayer")
        
        selected_questions = random.sample(all_questions, 10)
        question_ids = [str(q.id) for q in selected_questions]
        
        # Assign experts (same as single-player)
        expert_templates = [
            Expert(
                name="Dr. History",
                personality_type="Historian",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=historian",
                description="A cautious academic who values accuracy."
            ),
            Expert(
                name="Risk Taker",
                personality_type="Risky",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=risky",
                description="Overconfident and bold."
            ),
            Expert(
                name="The Skeptic",
                personality_type="Skeptical",
                avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=skeptic",
                description="Questions everything."
            )
        ]
        
        # Pick secret Saboteur
        saboteur = random.choice(expert_templates)
        
        # Create session
        session = MultiplayerGameSession(
            player1_id=player1_id,
            player2_id=player2_id,
            player1_socket_id=player1_socket_id,
            player2_socket_id=player2_socket_id,
            player1_status=PlayerState.CONNECTED,
            player2_status=PlayerState.CONNECTED,
            question_ids=question_ids,
            assigned_experts=expert_templates,
            saboteur_expert_name=saboteur.name,
            session_status=MultiplayerStatus.READY,
            started_at=datetime.utcnow(),
            question_start_time=datetime.utcnow()  # First question starts immediately
        )
        
        await session.insert()
        
        print(f"🎮 Multiplayer match created: {player1_id} vs {player2_id}")
        print(f"🎭 Saboteur: {saboteur.name}")
        
        return str(session.id)


# Global instance
matchmaking_queue = MatchmakingQueue()
