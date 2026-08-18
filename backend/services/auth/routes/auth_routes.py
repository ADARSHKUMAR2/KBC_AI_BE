from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from backend.services.auth.controllers.auth_controller import AuthController

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Request/Response models
class TokenVerifyRequest(BaseModel):
    """Unity sends this"""
    firebase_token: str
    
class UserResponse(BaseModel):
    """Backend returns this"""
    firebase_uid: str
    email: str
    display_name: str | None
    coins: int
    games_played: int
    games_won: int
    total_score: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "firebase_uid": "abc123",
                "email": "player@example.com",
                "display_name": "ProGamer",
                "coins": 1000,
                "games_played": 5,
                "games_won": 3,
                "total_score": 1500
            }
        }

@router.post("/verify", response_model=UserResponse)
async def verify_token(request: TokenVerifyRequest):
    """
    Unity Flow:
    1. User logs in with Firebase (email/password, Google, etc.)
    2. Firebase returns ID token
    3. Unity sends token to this endpoint
    4. Backend verifies + returns game profile
    
    Example Unity C# code:
    ```csharp
    string idToken = await FirebaseAuth.DefaultInstance.CurrentUser.GetIdTokenAsync(false);
    var response = await httpClient.PostAsync(
        "http://localhost:8000/auth/verify",
        new { firebase_token = idToken }
    );
    ```
    """
    user = await AuthController.verify_and_sync_user(request.firebase_token)
    
    return UserResponse(
        firebase_uid=user.firebase_uid,
        email=user.email,
        display_name=user.display_name,
        coins=user.coins,
        games_played=user.games_played,
        games_won=user.games_won,
        total_score=user.total_score
    )

@router.get("/profile", response_model=UserResponse)
async def get_profile(authorization: str = Header(...)):
    """
    Get current user's profile using their Firebase token.
    
    Unity sends: Authorization: Bearer <firebase_token>
    Backend returns: User profile with game data
    
    This is called after verify to fetch updated stats.
    """
    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    firebase_token = authorization.split("Bearer ")[1]
    user = await AuthController.verify_and_sync_user(firebase_token)
    
    return UserResponse(
        firebase_uid=user.firebase_uid,
        email=user.email,
        display_name=user.display_name,
        coins=user.coins,
        games_played=user.games_played,
        games_won=user.games_won,
        total_score=user.total_score
    )

@router.get("/test")
async def test_profile():
    return {"status": "Test"}
