from backend.shared.database import get_database
# Assuming you will create a User model in services/auth/models/user.py
from backend.services.auth.models.user import User

async def init_auth_db():
    """
    Initialize the database with Auth-specific models.
    """
    # Add all auth-related Beanie documents here
    models = [
        User,
        # TokenBlocklist, etc.
    ]
    await get_database(models)
