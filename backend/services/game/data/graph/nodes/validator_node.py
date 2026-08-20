
"""
graph/nodes/validator_node.py
------------------------------
Node 3 of the Phase 5 LangGraph pipeline.

Responsibility:
    Use the LLM as a quality judge to approve or reject the drafted question.
    Uses LangChain's with_structured_output() bound to ValidationResultSchema.

Input state fields used:
    draft_question   (dict) : The question from writer_node
    retry_count      (int)  : Current retry count (incremented here)

Output state fields written:
    is_valid          (bool)     : True = approved, False = retry
    validation_reason (str)      : Explanation from the judge
    retry_count       (int)      : Incremented by 1
    final_question    (dict|None): Set to draft if approved
"""

import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from backend.services.game.data.graph.state import QuestionGenState, ValidationResultSchema


# ── LLM client bound to ValidationResultSchema ───────────────────────────────
_base_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.2,          # Low temp for the judge = more consistent decisions
    api_key=os.getenv("GROQ_API_KEY")
)
validator_llm = _base_llm.with_structured_output(ValidationResultSchema, method="json_mode")


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a trivia question quality controller for a quiz game.

Approve the question ONLY if ALL of these are true:
1. The question is clearly worded and unambiguous.
2. Exactly one answer is definitively correct.
3. The 3 wrong answers are plausible — they sound like they could be right to someone who doesn't know.
4. The question is appropriate for a general audience (not offensive or politically biased).
5. The question can be answered without reading the original news article."""


async def validator_node(state: QuestionGenState) -> dict:
    """
    Validates the drafted question using an LLM as a judge.

    If approved → sets is_valid=True, promotes draft to final_question.
    If rejected → sets is_valid=False, increments retry_count.

    The conditional edge in question_graph.py reads is_valid + retry_count
    to decide whether to retry writer_node or proceed to saver_node.

    Returns a partial state update dict.
    """
    draft       = state.get("draft_question")
    retry_count = state.get("retry_count", 0)

    if not draft:
        print("⚠️  [Validator Node] No draft question found — skipping validation.")
        return {
            "is_valid":          False,
            "validation_reason": "No draft question to validate.",
            "retry_count":       retry_count + 1
        }

    print(f"🔎 [Validator Node] Validating: '{draft['question_text'][:60]}...'")

    # Format options for the judge to read
    options_text = "\n".join([
        f"{chr(65+i)}. {opt}" for i, opt in enumerate(draft["options"])
    ])

    user_prompt = f"""Question: {draft['question_text']}

Options:
{options_text}

Correct Answer: {chr(65 + draft['correct_answer'])}. {draft['options'][draft['correct_answer']]}

Evaluate this question against your quality criteria."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]

    try:
        # validator_llm returns a ValidationResultSchema object directly
        result: ValidationResultSchema = await validator_llm.ainvoke(messages)

        status_icon = "✅ APPROVED" if result.is_valid else "❌ REJECTED"
        print(f"   {status_icon}: {result.reason}")

        return {
            "is_valid":          result.is_valid,
            "validation_reason": result.reason,
            "retry_count":       retry_count + 1,
            # Promote to final_question only if approved
            "final_question":    draft if result.is_valid else state.get("final_question")
        }

    except Exception as e:
        # If the validator itself crashes, accept the draft as fallback
        # so we don't waste the writer's work on a validator bug.
        print(f"⚠️  [Validator Node] Crashed ({e}) — accepting draft as fallback.")
        return {
            "is_valid":          True,
            "validation_reason": f"Validator error — accepted as fallback: {e}",
            "retry_count":       retry_count + 1,
            "final_question":    draft
        }
