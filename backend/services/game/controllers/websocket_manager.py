from fastapi import WebSocket
from typing import Dict, Optional
import json
from datetime import datetime


class ConnectionManager:
    """
    Manages WebSocket connections for multiplayer games.
    
    Features:
    - Track active connections by player_id
    - Broadcast messages to specific players
    - Handle disconnections gracefully
    """
    
    def __init__(self):
        # Map: player_id → WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Map: session_id → [player1_id, player2_id]
        self.session_players: Dict[str, list] = {}
    
    async def connect(self, player_id: str, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[player_id] = websocket
        print(f"✅ WebSocket connected: {player_id}")
    
    def disconnect(self, player_id: str):
        """Remove WebSocket connection"""
        if player_id in self.active_connections:
            del self.active_connections[player_id]
            print(f"🔌 WebSocket disconnected: {player_id}")
    
    def register_session(self, session_id: str, player1_id: str, player2_id: str):
        """Track which players belong to which session"""
        self.session_players[session_id] = [player1_id, player2_id]
    
    async def send_to_player(self, player_id: str, message: dict):
        """Send message to specific player"""
        if player_id in self.active_connections:
            try:
                await self.active_connections[player_id].send_json(message)
            except Exception as e:
                print(f"❌ Failed to send to {player_id}: {e}")
                self.disconnect(player_id)
    
    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send message to both players in a session"""
        if session_id in self.session_players:
            player1_id, player2_id = self.session_players[session_id]
            await self.send_to_player(player1_id, message)
            await self.send_to_player(player2_id, message)
    
    async def send_personalized(
        self,
        session_id: str,
        player1_message: dict,
        player2_message: dict
    ):
        """Send different messages to each player (e.g., "You won!" vs "You lost!")"""
        if session_id in self.session_players:
            player1_id, player2_id = self.session_players[session_id]
            await self.send_to_player(player1_id, player1_message)
            await self.send_to_player(player2_id, player2_message)


# Global instance
connection_manager = ConnectionManager()
