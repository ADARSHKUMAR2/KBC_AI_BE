import os
import firebase_admin
from firebase_admin import credentials, auth

def init_firebase():
    """
    Initialize Firebase Admin SDK.
    
    This allows your backend to:
    1. Verify Firebase ID tokens sent from Unity
    2. Optionally create/manage Firebase users programmatically
    """
    try:
        # Check if Firebase is already initialized (prevents double-init errors)
        firebase_admin.get_app()
        print("✅ Firebase already initialized")
        return
    except ValueError:
        # Firebase not initialized yet, proceed with initialization
        pass
    
    # Path to your Firebase service account key
    # Download this from Firebase Console → Project Settings → Service Accounts
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cred_path = os.path.join(current_dir, "..", "serviceAccountKey.json")
    
    if not os.path.exists(cred_path):
        raise FileNotFoundError(
            f"❌ Firebase service account key not found at: {cred_path}\n"
            f"Download it from: Firebase Console → Project Settings → Service Accounts"
        )
    
    # Initialize Firebase with the service account credentials
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK initialized successfully")


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token sent from Unity.
    
    Args:
        id_token: The JWT token from Firebase Authentication
        
    Returns:
        dict: Decoded token containing user info (uid, email, etc.)
        
    Raises:
        Exception: If token is invalid, expired, or revoked
    """
    try:
        # This verifies:
        # - Token signature (cryptographically valid)
        # - Token hasn't expired
        # - Token wasn't revoked
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise Exception(f"Invalid Firebase token: {str(e)}")
