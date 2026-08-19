import asyncio
import json
import os
from pathlib import Path

# Import database and Question model
from backend.shared.database import get_database
from backend.services.game.models.question import Question


async def seed_questions():
    """
    Load questions from questions_seed.json into MongoDB.
    
    This script:
    1. Connects to MongoDB
    2. Reads questions_seed.json
    3. Clears existing questions (optional - see clear_existing flag)
    4. Inserts all questions from JSON file
    
    Run this with:
    python -m backend.services.game.data.seed_questions
    """
    
    print("🌱 Starting question seeding process...")
    
    # Initialize database
    try:
        await get_database(document_models=[Question])
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return

    # Check if questions already exist
    existing_count = await Question.count()
    
    if existing_count > 0:
        print(f"ℹ️  Database already has {existing_count} questions.")
        print("ℹ️  Skipping seed. Delete questions manually if you want to re-seed.")
        return
    
    # Load JSON file
    json_path = Path(__file__).parent / "questions_seed.json"
    
    if not json_path.exists():
        print(f"❌ JSON file not found at: {json_path}")
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        print(f"✅ Loaded {len(questions_data)} questions from JSON")
    except Exception as e:
        print(f"❌ Failed to read JSON file: {e}")
        return
    
    # Optional: Clear existing questions
    # WARNING: This deletes all questions in the database!
    clear_existing = True  # Set to False to keep existing questions
    
    if clear_existing:
        deleted_count = await Question.delete_all()
        print(f"🗑️  Deleted {deleted_count} existing questions")
    
    # Insert questions
    inserted_count = 0
    failed_count = 0
    
    for question_data in questions_data:
        try:
            question = Question(**question_data)
            await question.insert()
            inserted_count += 1
        except Exception as e:
            print(f"⚠️  Failed to insert question: {question_data.get('question_text', 'Unknown')}")
            print(f"   Error: {e}")
            failed_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Successfully inserted: {inserted_count} questions")
    if failed_count > 0:
        print(f"⚠️  Failed to insert: {failed_count} questions")
    print(f"{'='*60}\n")
    
    # Verify by counting
    total_in_db = await Question.count()
    print(f"📊 Total questions now in database: {total_in_db}")


# ========== RUN SCRIPT ==========

if __name__ == "__main__":
    """
    Run the seeding script.
    
    Usage:
    python -m backend.services.game.data.seed_questions
    
    Or from project root:
    cd backend
    python -m services.game.data.seed_questions
    """
    asyncio.run(seed_questions())
