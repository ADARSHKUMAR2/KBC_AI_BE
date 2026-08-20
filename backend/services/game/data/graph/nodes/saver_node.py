
"""
graph/nodes/saver_node.py
--------------------------
Node 4 (final) of the Phase 5 LangGraph pipeline.

Responsibility:
    Save the approved trivia question to MongoDB with category = "current_events".
    This is a pure database-write node — it does NOT call the LLM.

Input state fields used:
    final_question   (dict | None) : Validated question (preferred)
    draft_question   (dict | None) : Fallback if max retries were hit
    error            (str | None)  : Logged if pipeline failed earlier

Output state fields written:
    saved_question_id (str | None) : MongoDB _id of the saved document
    error             (str | None) : Set if DB write fails
"""

from backend.services.game.data.graph.state import QuestionGenState
from backend.services.game.models.question  import Question


async def saver_node(state: QuestionGenState) -> dict:
    """
    Saves the approved question to the MongoDB 'questions' collection.

    Priority:
    1. Use final_question (validator-approved)
    2. Fall back to draft_question (used when max retries reached with no approval)
    3. If neither exists, log error and return without saving

    The saved question has category="current_events" so it appears in
    the Daily News filter in Unity and the /game/questions/current-events endpoint.

    Returns a partial state update dict.
    """
    # Prefer the validator-approved version; fall back to raw draft
    question_data = state.get("final_question") or state.get("draft_question")
    prior_error   = state.get("error")

    if not question_data:
        err = prior_error or "No question data available to save."
        print(f"❌ [Saver Node] Cannot save — {err}")
        return {
            "saved_question_id": None,
            "error":             err
        }

    print(f"💾 [Saver Node] Saving to MongoDB: '{question_data['question_text'][:60]}...'")

    # Log whether we're saving a validated or fallback question
    is_validated = state.get("is_valid", False)
    if not is_validated:
        print("   ⚠️  Saving fallback draft (validator did not approve, max retries reached).")
    else:
        print(f"   ✅ Saving validator-approved question. Reason: {state.get('validation_reason', 'N/A')}")

    try:
        question = Question(
            question_text  = question_data["question_text"],
            options        = question_data["options"],
            correct_answer = int(question_data["correct_answer"]),
            difficulty     = question_data.get("difficulty", "medium"),
            category       = "current_events",                          # ← Phase 5 tag
            explanation    = question_data.get("explanation", "Based on recent news.")
        )

        await question.insert()

        print(f"✅ [Saver Node] Saved! MongoDB _id: {question.id}")

        return {
            "saved_question_id": str(question.id),
            "error":             None
        }

    except Exception as e:
        error_msg = f"Saver node DB write failed: {e}"
        print(f"❌ [Saver Node] {error_msg}")
        return {
            "saved_question_id": None,
            "error":             error_msg
        }
