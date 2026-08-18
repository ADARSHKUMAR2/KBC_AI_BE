import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv, find_dotenv
import certifi 
import sys
load_dotenv(find_dotenv())

async def get_database(document_models: list):
    """
    Initializes the database connection and Beanie ODM.
    """
    # Use MONGODB_URI to match your .env file
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("❌ MONGODB_URI is not set in the .env file!")

    db_name = os.getenv("MONGO_DB_NAME", "kbc_ai_db")
    
    # Create Motor client with uuid representation (fixes many Beanie issues)
    client = AsyncIOMotorClient(
                                mongo_uri,
                                uuidRepresentation="standard",
                                tlsCAFile=certifi.where()
                                )
    
    # Get the actual database object
    db = client.get_database(db_name)
    
    # Initialize Beanie
    await init_beanie(
        database=db,
        document_models=document_models
    )
    
    model_names = [m.__name__ for m in document_models]
    print(f"✅ Connected to MongoDB Atlas database '{db_name}' with models: {model_names}")
