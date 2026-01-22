"""Web search service for AI agent."""

import asyncio
import logging
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Maximum number of searches per request to prevent abuse
MAX_SEARCHES_PER_REQUEST = 3

# Search timeout in seconds
SEARCH_TIMEOUT = 10


async def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Execute a web search and return formatted results.

    Args:
        query: The search query
        max_results: Maximum number of results to return

    Returns:
        List of search results with title, link, and snippet
    """
    try:
        # Use DuckDuckGo search (no API key required)
        from duckduckgo_search import DDGS

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        results = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, max_results=max_results)),
            ),
            timeout=SEARCH_TIMEOUT,
        )

        # Format results
        formatted = []
        for result in results:
            formatted.append({
                "title": result.get("title", ""),
                "link": result.get("href", result.get("link", "")),
                "snippet": result.get("body", result.get("snippet", "")),
            })

        return formatted

    except ImportError:
        logger.warning("duckduckgo-search not installed, trying langchain-community")
        # Fallback to langchain-community's DuckDuckGo
        try:
            from langchain_community.tools import DuckDuckGoSearchResults

            search_tool = DuckDuckGoSearchResults(num_results=max_results)

            loop = asyncio.get_event_loop()
            raw_results = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: search_tool.run(query)),
                timeout=SEARCH_TIMEOUT,
            )

            # Parse langchain output (it's a string)
            # LangChain returns results as a formatted string
            return [{"title": "Search Results", "snippet": raw_results, "link": ""}]

        except ImportError:
            logger.error("No search backend available")
            return [{"title": "Error", "snippet": "Web search not available - install duckduckgo-search", "link": ""}]

    except TimeoutError:
        logger.warning(f"Search timeout for query: {query}")
        return [{"title": "Timeout", "snippet": "Search timed out, please try again", "link": ""}]

    except Exception as e:
        logger.error(f"Search error: {e}")
        return [{"title": "Error", "snippet": f"Search failed: {e!s}", "link": ""}]


def format_search_results(results: list[dict[str, Any]]) -> str:
    """
    Format search results as a string for inclusion in prompts.

    Args:
        results: List of search result dictionaries

    Returns:
        Formatted string representation of search results
    """
    if not results:
        return "No search results found."

    formatted_parts = []
    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        link = result.get("link", "")
        snippet = result.get("snippet", "")

        parts = [f"{i}. {title}"]
        if link:
            parts.append(f"   URL: {link}")
        if snippet:
            parts.append(f"   {snippet}")

        formatted_parts.append("\n".join(parts))

    return "\n\n".join(formatted_parts)


async def execute_searches(queries: list[str]) -> str:
    """
    Execute multiple search queries and return combined results.

    Limits the number of searches to prevent abuse.

    Args:
        queries: List of search queries

    Returns:
        Combined formatted search results
    """
    if not queries:
        return ""

    # Limit number of searches
    limited_queries = queries[:MAX_SEARCHES_PER_REQUEST]
    if len(queries) > MAX_SEARCHES_PER_REQUEST:
        logger.warning(
            f"Limiting searches from {len(queries)} to {MAX_SEARCHES_PER_REQUEST}"
        )

    all_results = []
    for query in limited_queries:
        results = await search_web(query)
        if results:
            all_results.append(f"## Search: {query}\n{format_search_results(results)}")

    return "\n\n".join(all_results)


def is_search_available() -> bool:
    """
    Check if web search functionality is available.

    Returns:
        True if search is available, False otherwise
    """
    try:
        from duckduckgo_search import DDGS  # noqa: F401

        return True
    except ImportError:
        try:
            from langchain_community.tools import DuckDuckGoSearchResults  # noqa: F401

            return True
        except ImportError:
            return False
