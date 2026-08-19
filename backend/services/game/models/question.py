from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime

class Question(Document):
    """
    Represents a single trivia question in the game.
    
    This model stores all question data in MongoDB, including:
    - The question text
    - Four multiple choice options
    - The correct answer index (0-3)
    - Metadata like difficulty and category
    """
    
    # The actual question text shown to the player
    question_text: str = Field(..., min_length=10)
    
    # Four answer options (always exactly 4 for consistency)
    # Example: ["Paris", "London", "Berlin", "Madrid"]
    options: List[str] = Field(..., min_length=4, max_length=4)
    
    # Index of the correct answer in the options list (0, 1, 2, or 3)
    # If correct answer is "Paris" at index 0, this would be 0
    correct_answer: int = Field(..., ge=0, le=3)
    
    # Difficulty level: "easy", "medium", "hard"
    difficulty: str = Field(default="medium")
    
    # Category: "history", "science", "geography", "entertainment", etc.
    category: str = Field(default="general")
    
    # Explanation shown after the player answers
    # Example: "Paris is the capital of France, established in the 3rd century BC."
    explanation: Optional[str] = None
    
    # When this question was added to the database
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "questions"  # MongoDB collection name
    
    class Config:
        json_schema_extra = {
            "example": {
                "question_text": "What is the capital of France?",
                "options": ["Paris", "London", "Berlin", "Madrid"],
                "correct_answer": 0,
                "difficulty": "easy",
                "category": "geography",
                "explanation": "Paris has been the capital of France since the 12th century."
            }
        }
