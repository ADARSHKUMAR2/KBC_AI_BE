"""
graph/nodes/writer_node.py
---------------------------
Node 2 of the Phase 5 LangGraph pipeline.

Responsibility:
    Pick one news story and use the LLM to draft a trivia question.
    Uses LangChain's with_structured_output() — no JSON parsing needed.

Input state fields used:
    news_stories (list[dict]) : Articles from research_node
    retry_count  (int)        : Used to pick a different story on retry

Output state fields written:
    chosen_story   (dict)     : The article used for this draft
    draft_question (dict)     : The LLM-generated MCQ as a dict
    error          (str|None) : Set if LLM call fails
"""

import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from backend.services.game.data.graph.state import QuestionGenState, DraftQuestionSchema


# ── LLM client bound to DraftQuestionSchema ─────────────────────────────────
# method="json_mode" uses Groq's native JSON output (faster, more reliable
# than tool-calling for simple structured responses).
_base_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.8,          # Slightly higher temp = more creative questions
    api_key=os.getenv("GROQ_API_KEY")
)
writer_llm = _base_llm.with_structured_output(DraftQuestionSchema, method="json_mode")


# ── System Prompt ─────────────────────────────────────────────────────────────
# No JSON format instructions needed — LangChain injects the schema.
SYSTEM_PROMPT = """You are a professional trivia question writer for a "Who Wants to be a Millionaire" style game.

Your job: Read a news article and write ONE multiple-choice trivia question based on it.

Rules:
1. The question must be factual and based ONLY on the news article provided.
2. There must be exactly 4 options. Only ONE is correct; the other 3 must be plausible but wrong.
3. The question should be answerable by someone who read the headline and summary.
4. Difficulty should be "medium" — not trivially obvious, not impossibly obscure.
5. The explanation should clearly justify the correct answer in one sentence."""


async def writer_node(state: QuestionGenState) -> dict:
    """
    Drafts a trivia question from a selected news story.

    On retry (retry_count > 0), cycles to the next story in the list
    so we don't keep generating bad questions from the same source.

    Returns a partial state update dict.
    """
    stories     = state.get("news_stories", [])
    retry_count = state.get("retry_count", 0)

    if not stories:
        return {
            "draft_question": None,
            "error": "No news stories in state — research_node may have failed."
        }

    # Cycle through stories on retry to avoid hammering the same article
    story_index  = retry_count % len(stories)
    chosen_story = stories[story_index]

    print(f"✍️  [Writer Node] Using story #{story_index+1}: '{chosen_story['title'][:60]}...'")
    if retry_count > 0:
        print(f"   (Retry #{retry_count})")

    user_prompt = f"""News Article:
Title:   {chosen_story['title']}
Source:  {chosen_story['source']}
Summary: {chosen_story['description']}

Write a trivia question based on this article."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]

    try:
        # writer_llm returns a DraftQuestionSchema object directly
        draft: DraftQuestionSchema = await writer_llm.ainvoke(messages)

        print(f"   📝 Question:       {draft.question_text[:80]}...")
        print(f"   ✅ Correct answer: Option {draft.correct_answer+1}: {draft.options[draft.correct_answer]}")

        return {
            "chosen_story":   chosen_story,
            "draft_question": draft.model_dump(),   # store as plain dict in state
            "error":          None
        }

    except Exception as e:
        # Catches Pydantic ValidationError (wrong schema) + network errors
        error_msg = f"Writer node failed: {e}"
        print(f"❌ [Writer Node] {error_msg}")
        return {
            "draft_question": None,
            "error":          error_msg
        }
