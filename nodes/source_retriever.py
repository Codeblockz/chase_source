"""
Source retrieval node using Tavily.
"""

import logging

from tavily import TavilyClient

from config import settings
from schemas.models import GraphState, SearchResult

logger = logging.getLogger(__name__)
tavily = TavilyClient(api_key=settings.tavily_api_key)


def retrieve_sources(state: GraphState) -> GraphState:
    """
    Retrieve sources from Tavily for the extracted claim.

    Args:
        state: Current graph state with extracted_claim

    Returns:
        Updated state with search_results
    """
    claim = state["extracted_claim"]
    if not claim:
        logger.warning("No claim to search for")
        return {**state, "search_results": [], "search_query": None}

    # Build search query from claim
    search_query = claim.claim
    logger.info(f"Searching Tavily: {search_query}")

    try:
        response = tavily.search(
            query=search_query,
            search_depth=settings.tavily_search_depth,
            max_results=settings.tavily_max_results,
            include_raw_content=True,
        )

        results = []
        for item in response.get("results", []):
            try:
                result = SearchResult(
                    url=item["url"],
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    published_date=item.get("published_date"),
                    raw_content=item.get("raw_content"),
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"Skipping malformed result: {e}")
                continue

        logger.info(f"Retrieved {len(results)} search results")
        return {**state, "search_results": results, "search_query": search_query}

    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return {
            **state,
            "search_results": [],
            "search_query": search_query,
            "errors": state.get("errors", []) + [f"Source retrieval: {e}"],
        }
