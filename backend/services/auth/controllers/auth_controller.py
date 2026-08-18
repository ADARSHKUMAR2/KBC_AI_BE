from fastapi import HTTPException, status
from backend.services.auth.models.user import User
from backend.services.auth.config.firebase import verify_firebase_token
from datetime import datetime

class AuthController:
    """
    Handles authentication business logic.
    """
    
    @staticmethod
    async def verify_and_sync_user(firebase_token: str) -> User:
        """
        Main authentication flow:
        1. Verify Firebase token (is this user legit?)
        2. Check if user exists in MongoDB
        3. If new user → create profile
        4. If existing user → update last_login
        5. Return user profile
        
        Args:
            firebase_token: JWT token from Unity's Firebase SDK
            
        Returns:
            User: Complete user profile with game data
        """
        try:
            # Step 1: Verify token with Firebase
            decoded_token = verify_firebase_token(firebase_token)
            
            # Extract user info from Firebase token
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email')
            display_name = decoded_token.get('name')
            photo_url = decoded_token.get('picture')
            
            # Step 2: Check if user exists in MongoDB
            user = await User.find_one(User.firebase_uid == firebase_uid)
            
            if user:
                # Existing user - update last login time
                user.last_login = datetime.utcnow()
                
                # Update display name/photo if changed in Firebase
                if display_name:
                    user.display_name = display_name
                if photo_url:
                    user.photo_url = photo_url
                    
                await user.save()
                print(f"✅ Existing user logged in: {email}")
            else:
                # New user - create profile in MongoDB
                user = User(
                    firebase_uid=firebase_uid,
                    email=email,
                    display_name=display_name,
                    photo_url=photo_url,
                    coins=1000,  # Starting coins
                    games_played=0,
                    games_won=0,
                    total_score=0
                )
                await user.insert()
                print(f"✅ New user created: {email}")
            
            return user
            
        except Exception as e:
            # Token verification failed or database error
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )
    
    @staticmethod
    async def get_user_by_firebase_uid(firebase_uid: str) -> User:
        """
        Fetch user profile from MongoDB using Firebase UID.
        
        Used by other services (e.g., Game service needs user's coins).
        """
        user = await User.find_one(User.firebase_uid == firebase_uid)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        return user
