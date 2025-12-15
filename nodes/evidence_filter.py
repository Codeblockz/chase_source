"""
Evidence filtering node.
"""

import json
import logging

from openai import OpenAI

from config import settings
from prompts.templates import (
    EVIDENCE_RELEVANCE_SYSTEM,
    EVIDENCE_RELEVANCE_USER,
    SOURCE_CLASSIFICATION_SYSTEM,
    SOURCE_CLASSIFICATION_USER,
)
from schemas.models import Evidence, GraphState, SearchResult, SourceType

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def classify_source(url: str, title: str, content: str) -> SourceType:
    """Classify source type using LLM."""
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=500,
            messages=[
                {"role": "system", "content": SOURCE_CLASSIFICATION_SYSTEM},
                {
                    "role": "user",
                    "content": SOURCE_CLASSIFICATION_USER.format(
                        url=url, title=title, content=content[:1000]
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return SourceType(result.get("source_type", "unknown"))
    except Exception as e:
        logger.warning(f"Source classification failed: {e}")
        return SourceType.UNKNOWN


def assess_relevance(claim: str, result: SearchResult) -> dict | None:
    """Assess relevance and extract evidence from a search result."""
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": EVIDENCE_RELEVANCE_SYSTEM},
                {
                    "role": "user",
                    "content": EVIDENCE_RELEVANCE_USER.format(
                        claim=claim,
                        url=str(result.url),
                        title=result.title,
                        content=result.content[:3000],
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.warning(f"Relevance assessment failed: {e}")
        return None


def filter_evidence(state: GraphState) -> GraphState:
    """
    Filter search results for relevant evidence.

    Args:
        state: Current graph state with search_results and extracted_claim

    Returns:
        Updated state with filtered evidence list
    """
    claim = state.get("extracted_claim")
    results = state.get("search_results", [])

    if not claim or not results:
        logger.warning("No claim or search results to filter")
        return {**state, "evidence": []}

    claim_text = claim.claim
    evidence_list = []

    for result in results:
        # Assess relevance
        assessment = assess_relevance(claim_text, result)
        if not assessment:
            continue

        if not assessment.get("is_relevant", False):
            logger.debug(f"Filtered out: {result.title} (not relevant)")
            continue

        if assessment.get("relevance_score", 0) < 0.5:
            logger.debug(f"Filtered out: {result.title} (low score)")
            continue

        # Classify source type
        source_type = classify_source(str(result.url), result.title, result.content)

        # Build evidence object
        try:
            evidence = Evidence(
                source_url=result.url,
                source_title=result.title,
                source_type=source_type,
                verbatim_quote=assessment["verbatim_quote"],
                relevance_score=assessment["relevance_score"],
                relevance_explanation=assessment["relevance_explanation"],
            )
            evidence_list.append(evidence)
            logger.info(f"Found evidence: {result.title} ({source_type.value})")
        except Exception as e:
            logger.warning(f"Failed to create evidence object: {e}")
            continue

        # Limit to top 5 evidence items
        if len(evidence_list) >= 5:
            break

    # Sort by relevance score
    evidence_list.sort(key=lambda e: e.relevance_score, reverse=True)

    logger.info(f"Filtered to {len(evidence_list)} evidence items")
    return {**state, "evidence": evidence_list}
