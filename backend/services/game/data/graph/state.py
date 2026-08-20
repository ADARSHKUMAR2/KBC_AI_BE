"""
graph/state.py
--------------
Shared state and Pydantic schemas for the Phase 5 LangGraph pipeline.

All nodes import QuestionGenState from here.
All structured LLM outputs are defined here as Pydantic models.

Why separate?
- Avoids circular imports (nodes import state, graph imports nodes + state)
- Single source of truth — change a field once, all nodes see it
- Easy to add new state fields without touching node logic
"""

from typing import TypedDict, Optional
from pydantic import BaseModel, Field as PydanticField


# ═══════════════════════════════════════════════════════════════════════════
# PYDANTIC RESPONSE SCHEMAS
# Used with LangChain's .with_structured_output() — no json.loads() needed.
# ═══════════════════════════════════════════════════════════════════════════

class DraftQuestionSchema(BaseModel):
    """
    Schema for the Writer Node's LLM output.
    LangChain enforces this structure — the LLM cannot return malformed data.
    """
    question_text: str = PydanticField(
        description="The trivia question, clearly and unambiguously worded."
    )
    options: list[str] = PydanticField(
        description="Exactly 4 answer options. Only one is correct, the other 3 are plausible distractors.",
        min_length=4,
        max_length=4
    )
    correct_answer: int = PydanticField(
        description="0-based index of the correct option in the options list (0, 1, 2, or 3).",
        ge=0,
        le=3
    )
    explanation: str = PydanticField(
        description="One sentence explaining why the correct answer is right."
    )
    difficulty: str = PydanticField(
        default="medium",
        description="Difficulty level: 'easy', 'medium', or 'hard'."
    )
    news_source: str = PydanticField(
        default="",
        description="Name of the news publication this question is based on."
    )


class ValidationResultSchema(BaseModel):
    """
    Schema for the Validator Node's LLM output.
    The LLM judge returns a structured approval/rejection decision.
    """
    is_valid: bool = PydanticField(
        description="True if the question meets all quality standards, False to reject and retry."
    )
    reason: str = PydanticField(
        description="One sentence explaining the approval or rejection decision."
    )


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH STATE
# ═══════════════════════════════════════════════════════════════════════════

class QuestionGenState(TypedDict):
    """
    The shared state object that flows through every node in the graph.

    LangGraph passes this dict to each node. Each node returns a partial
    update dict — LangGraph merges it into the state automatically.

    Fields:
        news_stories      : Raw articles from NewsAPI (set by research_node)
        chosen_story      : The article selected for trivia (set by writer_node)
        draft_question    : The LLM-drafted MCQ as dict (set by writer_node)
        is_valid          : Whether Validator approved the question
        validation_reason : Why the Validator accepted or rejected
        retry_count       : How many Writer retries have occurred
        final_question    : The approved question dict (set by validator_node)
        saved_question_id : MongoDB _id string after saving (set by saver_node)
        error             : Any error message for graceful failure logging
    """
    news_stories:       list[dict]
    chosen_story:       Optional[dict]
    draft_question:     Optional[dict]
    is_valid:           bool
    validation_reason:  str
    retry_count:        int
    final_question:     Optional[dict]
    saved_question_id:  Optional[str]
    error:              Optional[str]
