from pydantic import BaseModel, Field
from typing import Optional

class Expert(BaseModel):
    """
    Represents one of the three AI experts in the game.
    
    NOTE: This is NOT a Beanie Document - it's embedded inside GameSession.
    Each expert has a personality type that determines how they give advice.
    
    In Phase 2: Hardcoded advice logic
    In Phase 4: Will use LLM prompts based on personality_type
    """
    
    # Expert's display name shown in Unity UI
    # Example: "Dr. History", "Risk Taker", "The Skeptic"
    name: str
    
    # Determines advice behavior (case-sensitive)
    # Options: "Historian", "Risky", "Skeptical"
    # Later in Phase 3, one can be secretly a "Saboteur"
    personality_type: str = Field(..., pattern="^(Historian|Risky|Skeptical|Saboteur)$")
    
    # URL to the expert's avatar image (for Unity to display)
    # Example: "https://example.com/avatars/historian.png"
    avatar_url: Optional[str] = None
    
    # Short bio shown when hovering over the expert
    # Example: "A cautious academic who values accuracy over speed."
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Dr. History",
                "personality_type": "Historian",
                "avatar_url": "https://placekitten.com/200/200",
                "description": "An expert historian who provides well-researched, cautious advice."
            }
        }


class ExpertAdvice(BaseModel):
    """
    Represents the advice given by an expert for a specific question.
    
    This is returned to Unity when fetching a question.
    Each of the 3 experts will have one of these per question.
    """
    
    # Which expert is giving this advice
    expert_name: str
    
    # The actual advice text (hardcoded in Phase 2, LLM-generated in Phase 4)
    # Example: "I'm 85% certain it's option A based on historical records."
    advice_text: str
    
    # How confident the expert claims to be (0-100)
    # This is part of the psychological game - high confidence doesn't mean correct!
    confidence_percentage: int = Field(..., ge=0, le=100)
    
    # Which option index (0-3) the expert recommends
    recommended_option: int = Field(..., ge=0, le=3)
    
    class Config:
        json_schema_extra = {
            "example": {
                "expert_name": "Dr. History",
                "advice_text": "Based on historical records, I believe option 1 is correct.",
                "confidence_percentage": 85,
                "recommended_option": 0
            }
        }
