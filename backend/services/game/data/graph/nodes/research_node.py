"""
graph/nodes/research_node.py
-----------------------------
Node 1 of the Phase 5 LangGraph pipeline.

Responsibility:
    Fetch real-time news stories from NewsAPI and store them in graph state.
    This is a pure data-fetching node — it does NOT call the LLM.

Input state fields used:
    (none — this is the entry node)

Output state fields written:
    news_stories (list[dict]) : The fetched articles
    error        (str | None) : Set if fetching fails
"""

from backend.services.game.data.graph.state import QuestionGenState
from backend.services.game.data.news_fetcher import fetch_mixed_news


async def research_node(state: QuestionGenState) -> dict:
    """
    Fetches today's top news stories from multiple categories.

    Uses fetch_mixed_news() which internally calls NewsAPI across
    technology, science, general, and health categories, then deduplicates
    and shuffles for variety.

    Returns a partial state update dict.
    """
    print("🔍 [Research Node] Fetching today's news...")

    try:
        stories = await fetch_mixed_news(max_stories=6)

        if not stories:
            print("⚠️  [Research Node] NewsAPI returned 0 usable stories.")
            return {
                "news_stories": [],
                "error": "NewsAPI returned 0 usable stories today."
            }

        print(f"📰 [Research Node] Got {len(stories)} stories:")
        for i, story in enumerate(stories):
            print(f"   {i+1}. [{story['source']}] {story['title'][:70]}...")

        return {
            "news_stories": stories,
            "error":        None
        }

    except Exception as e:
        error_msg = f"Research node failed: {e}"
        print(f"❌ [Research Node] {error_msg}")
        return {
            "news_stories": [],
            "error":        error_msg
        }
