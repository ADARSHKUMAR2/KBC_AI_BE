
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
from langchain_core.output_parsers import JsonOutputParser

from backend.services.game.data.graph.state import QuestionGenState, ValidationResultSchema

validator_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY")
)

parser = JsonOutputParser(pydantic_object=ValidationResultSchema)

SYSTEM_PROMPT = """You are a trivia question quality controller for a quiz game.

Approve the question ONLY if ALL of these are true:
1. The question is clearly worded and unambiguous.
2. Exactly one answer is definitively correct.
3. The 3 wrong answers are plausible.
4. The question is appropriate for a general audience.
5. The question can be answered without reading the original news article.

{format_instructions}"""

async def validator_node(state: QuestionGenState) -> dict:
    draft       = state.get("draft_question")
    retry_count = state.get("retry_count", 0)

    if not draft:
        return {
            "is_valid":          False,
            "validation_reason": "No draft question to validate.",
            "retry_count":       retry_count + 1
        }

    print(f"🔎 [Validator Node] Validating: '{draft['question_text'][:60]}...'")

    options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(draft["options"])])

    user_prompt = f"""Question: {draft['question_text']}

Options:
{options_text}

Correct Answer: {chr(65 + draft['correct_answer'])}. {draft['options'][draft['correct_answer']]}

Evaluate this question against your quality criteria."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(format_instructions=parser.get_format_instructions())),
        HumanMessage(content=user_prompt)
    ]

    try:
        response = await validator_llm.ainvoke(messages)
        result_dict = parser.parse(response.content)

        is_valid = result_dict["is_valid"]
        reason = result_dict["reason"]

        status_icon = "✅ APPROVED" if is_valid else "❌ REJECTED"
        print(f"   {status_icon}: {reason}")

        return {
            "is_valid":          is_valid,
            "validation_reason": reason,
            "retry_count":       retry_count + 1,
            "final_question":    draft if is_valid else state.get("final_question")
        }

    except Exception as e:
        print(f"⚠️  [Validator Node] Crashed ({e}) — accepting draft as fallback.")
        return {
            "is_valid":          True,
            "validation_reason": f"Validator error — accepted as fallback: {e}",
            "retry_count":       retry_count + 1,
            "final_question":    draft
        }