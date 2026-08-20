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
from langchain_core.output_parsers import JsonOutputParser

from backend.services.game.data.graph.state import QuestionGenState, DraftQuestionSchema

# Pure text generation LLM
writer_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.8,
    api_key=os.getenv("GROQ_API_KEY")
)

# Parser that forces output into DraftQuestionSchema
parser = JsonOutputParser(pydantic_object=DraftQuestionSchema)

SYSTEM_PROMPT = """You are a professional trivia question writer for a "Who Wants to be a Millionaire" style game.

Your job: Read a news article and write ONE multiple-choice trivia question based on it.

Rules:
1. The question must be factual and based ONLY on the news article provided.
2. There must be exactly 4 options. Only ONE is correct; the other 3 must be plausible but wrong.
3. The question should be answerable by someone who read the headline and summary.
4. Difficulty should be "medium".
5. The explanation should clearly justify the correct answer.

{format_instructions}"""

async def writer_node(state: QuestionGenState) -> dict:
    stories     = state.get("news_stories", [])
    retry_count = state.get("retry_count", 0)

    if not stories:
        return {"draft_question": None, "error": "No news stories available."}

    story_index  = retry_count % len(stories)
    chosen_story = stories[story_index]

    print(f"✍️  [Writer Node] Using story #{story_index+1}: '{chosen_story['title'][:60]}...'")

    user_prompt = f"""News Article:
Title:   {chosen_story['title']}
Source:  {chosen_story['source']}
Summary: {chosen_story['description']}

Write a trivia question based on this article."""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(format_instructions=parser.get_format_instructions())),
        HumanMessage(content=user_prompt)
    ]

    try:
        response = await writer_llm.ainvoke(messages)
        # Parse the raw text into our Pydantic dict
        draft_dict = parser.parse(response.content)

        print(f"   📝 Question:       {draft_dict['question_text'][:80]}...")
        print(f"   ✅ Correct answer: Option {draft_dict['correct_answer']+1}: {draft_dict['options'][draft_dict['correct_answer']]}")

        return {
            "chosen_story":   chosen_story,
            "draft_question": draft_dict,
            "error":          None
        }

    except Exception as e:
        error_msg = f"Writer node failed: {e}"
        print(f"❌ [Writer Node] {error_msg}")
        return {"draft_question": None, "error": error_msg}