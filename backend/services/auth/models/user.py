from beanie import Document
from pydantic import Field, EmailStr, BaseModel
from typing import Optional
from datetime import datetime

class User(Document):
    """
    User profile stored in MongoDB.
    
    Firebase handles: authentication, passwords, email verification
    MongoDB stores: game data, coins, statistics, preferences
    """
    
    # Firebase UID is the unique identifier
    firebase_uid: str = Field(..., unique=True, index=True)
    
    # User information (synced from Firebase on first login)
    email: EmailStr
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    
    # Game-specific data (not stored in Firebase)
    coins: int = Field(default=1000)  # Starting coins
    games_played: int = Field(default=0)
    games_won: int = Field(default=0)
    total_score: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "users"  # MongoDB collection name
        
    class Config:
        json_schema_extra = {
            "example": {
                "firebase_uid": "abc123xyz",
                "email": "player@example.com",
                "display_name": "ProGamer123",
                "coins": 1000,
                "games_played": 5,
                "games_won": 3
            }
        }

class TokenVerifyRequest(BaseModel):
    firebase_token: str
    email: Optional[str] = None
    display_name: Optional[str] = None