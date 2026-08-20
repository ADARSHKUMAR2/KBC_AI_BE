"""
news_fetcher.py
---------------
Fetches real-time news headlines from NewsAPI.org.
Used by the LangGraph question-generation pipeline (Phase 5).

The Research Node calls `fetch_top_news()` to get today's stories,
which are then passed to the Writer Node to draft trivia questions.
"""

import os
import httpx
from typing import Optional
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_BASE = "https://newsapi.org/v2"

async def fetch_top_news(
    category: str = "general",
    country: str = "us",
    max_stories: int = 5
) -> list[dict]:
    """
    Fetch today's top news headlines asynchronously using httpx.

    Args:
        category:    NewsAPI category — "general", "technology", "science",
                     "health", "business", "sports", "entertainment"
        country:     Two-letter country code (default "in")
        max_stories: Maximum number of stories to return

    Returns:
        List of story dicts, each with keys:
            - title (str):       Headline text
            - description (str): Short summary
            - source (str):      Publication name
            - url (str):         Article URL
            - published_at (str): ISO timestamp

    Raises:
        RuntimeError: If the API key is missing or the API call fails
    """
    if not NEWS_API_KEY:
        raise RuntimeError(
            "NEWS_API_KEY is not set in .env — "
            "sign up at https://newsapi.org to get a free key."
        )

    params = {
        "apiKey":   NEWS_API_KEY,
        "category": category,
        "country":  country,
        "pageSize": max_stories,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{NEWS_API_BASE}/top-headlines", params=params)

    if response.status_code != 200:
        raise RuntimeError(
            f"NewsAPI returned {response.status_code}: {response.text}"
        )

    data = response.json()

    if data.get("status") != "ok":
        raise RuntimeError(f"NewsAPI error: {data.get('message', 'unknown error')}")

    articles = data.get("articles", [])

    # Filter out articles with missing title or description (useless for trivia)
    stories = []
    for article in articles:
        title = (article.get("title") or "").strip()
        description = (article.get("description") or "").strip()

        # Skip "[Removed]" placeholder articles NewsAPI sometimes returns
        if not title or title == "[Removed]" or not description:
            continue

        stories.append({
            "title":        title,
            "description":  description,
            "source":       article.get("source", {}).get("name", "Unknown"),
            "url":          article.get("url", ""),
            "published_at": article.get("publishedAt", ""),
        })

    return stories[:max_stories]


async def fetch_mixed_news(max_stories: int = 5) -> list[dict]:
    """
    Convenience helper: fetch stories from multiple categories
    so we get a variety of question topics per day.

    Tries technology + science + general, then merges and deduplicates.
    """
    import random

    categories = ["technology", "science", "general", "health"]
    all_stories: list[dict] = []

    for category in categories:
        try:
            stories = await fetch_top_news(category=category, max_stories=3)
            all_stories.extend(stories)
        except RuntimeError as e:
            # Don't crash the whole pipeline if one category fails
            print(f"⚠️  Could not fetch '{category}' news: {e}")
            continue

    # Deduplicate by title
    seen_titles: set[str] = set()
    unique_stories: list[dict] = []
    for story in all_stories:
        if story["title"] not in seen_titles:
            seen_titles.add(story["title"])
            unique_stories.append(story)

    # Shuffle for variety, then return up to max_stories
    random.shuffle(unique_stories)
    return unique_stories[:max_stories]
