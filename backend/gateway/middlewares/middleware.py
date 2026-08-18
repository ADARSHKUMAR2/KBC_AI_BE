from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.auth.config.firebase import verify_firebase_token

class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    """
    Validates Firebase tokens on protected routes.
    
    Flow:
    1. Unity → Gateway (with Authorization header)
    2. Middleware intercepts request
    3. Extracts + verifies Firebase token
    4. Attaches user info to request
    5. Passes to backend service
    
    Protected routes require: Authorization: Bearer <firebase_token>
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        public_paths = [
            "/",
            "/health",
            "/auth/verify",  # First login doesn't need auth
        ]
        
        if request.url.path in public_paths:
            return await call_next(request)
        
        # All other routes require authentication
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing Authorization header"}
            )
        
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid Authorization header format. Use: Bearer <token>"}
            )
        
        # Extract token
        firebase_token = auth_header.split("Bearer ")[1]
        
        try:
            # Verify with Firebase
            decoded_token = verify_firebase_token(firebase_token)
            
            # Attach user info to request state (available to all downstream handlers)
            request.state.firebase_uid = decoded_token['uid']
            request.state.user_email = decoded_token.get('email')
            
            # Continue to the actual endpoint
            response = await call_next(request)
            return response
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Invalid or expired token: {str(e)}"}
            )
