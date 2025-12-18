"""
Evidence filtering node with parallel processing.
"""

import asyncio
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import settings
from prompts.templates import (
    EVIDENCE_RELEVANCE_SYSTEM,
    EVIDENCE_RELEVANCE_USER,
    SOURCE_CLASSIFICATION_SYSTEM,
    SOURCE_CLASSIFICATION_USER,
)
from schemas.models import (
    Evidence,
    EvidenceRelevanceResponse,
    GraphState,
    SearchResult,
    SourceClassificationResponse,
    SourceType,
)

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.0,
    api_key=settings.openai_api_key,
)

# Classification chain
classification_llm = llm.with_structured_output(SourceClassificationResponse)
classification_prompt = ChatPromptTemplate.from_messages([
    ("system", SOURCE_CLASSIFICATION_SYSTEM),
    ("user", SOURCE_CLASSIFICATION_USER),
])
classification_chain = classification_prompt | classification_llm

# Relevance chain
relevance_llm = llm.with_structured_output(EvidenceRelevanceResponse)
relevance_prompt = ChatPromptTemplate.from_messages([
    ("system", EVIDENCE_RELEVANCE_SYSTEM),
    ("user", EVIDENCE_RELEVANCE_USER),
])
relevance_chain = relevance_prompt | relevance_llm


async def assess_and_classify(claim: str, result: SearchResult) -> Evidence | None:
    """Assess relevance and classify source in parallel."""
    try:
        # Run relevance and classification in parallel
        relevance_task = relevance_chain.ainvoke({
            "claim": claim,
            "url": str(result.url),
            "title": result.title,
            "content": result.content[:3000],
        })
        classification_task = classification_chain.ainvoke({
            "url": str(result.url),
            "title": result.title,
            "content": result.content[:1000],
        })

        relevance_result, classification_result = await asyncio.gather(
            relevance_task, classification_task
        )

        # Check relevance criteria
        if not relevance_result.is_relevant:
            logger.debug(f"Filtered out: {result.title} (not relevant)")
            return None

        if relevance_result.relevance_score < 0.5:
            logger.debug(f"Filtered out: {result.title} (low score)")
            return None

        # Ensure the quote is actually present (or substantially present) in the retrieved content to prevent hallucinated quotes
        quote = relevance_result.verbatim_quote
        source_text = (result.raw_content or result.content or "").lower()
        if quote:
            normalized_quote = quote.strip().lower()
            if normalized_quote not in source_text:
                # Allow minor wording differences: require at least 60% token overlap
                q_tokens = normalized_quote.split()
                if q_tokens:
                    overlap = sum(1 for t in q_tokens if t in source_text.split()) / len(
                        q_tokens
                    )
                else:
                    overlap = 0
                if overlap < 0.6:
                    logger.debug(
                        f"Filtered out: {result.title} (quote not found verbatim in source)"
                    )
                    relevance_result.verbatim_quote = None

        if not relevance_result.verbatim_quote:
            logger.debug(f"Filtered out: {result.title} (no quote)")
            return None

        source_type = SourceType(classification_result.source_type)

        evidence = Evidence(
            source_url=result.url,
            source_title=result.title,
            source_type=source_type,
            verbatim_quote=relevance_result.verbatim_quote,
            relevance_score=relevance_result.relevance_score,
            relevance_explanation=relevance_result.relevance_explanation,
        )
        logger.info(f"Found evidence: {result.title} ({source_type.value})")
        return evidence

    except Exception as e:
        logger.warning(f"Evidence assessment failed for {result.title}: {e}")
        return None


async def filter_evidence_async(state: GraphState) -> GraphState:
    """Filter search results for relevant evidence using parallel processing."""
    claim = state.get("extracted_claim")
    results = state.get("search_results", [])

    if not claim or not results:
        logger.warning("No claim or search results to filter")
        return {**state, "evidence": []}

    claim_text = claim.claim

    # Process all results in parallel
    tasks = [assess_and_classify(claim_text, result) for result in results]
    evidence_results = await asyncio.gather(*tasks)

    # Filter out None results and sort by relevance
    evidence_list = [e for e in evidence_results if e is not None]
    evidence_list.sort(key=lambda e: e.relevance_score, reverse=True)

    # Limit to top 5
    evidence_list = evidence_list[:5]

    logger.info(f"Filtered to {len(evidence_list)} evidence items")
    return {**state, "evidence": evidence_list}


def filter_evidence(state: GraphState) -> GraphState:
    """
    Filter search results for relevant evidence.

    Args:
        state: Current graph state with search_results and extracted_claim

    Returns:
        Updated state with filtered evidence list
    """
    return asyncio.run(filter_evidence_async(state))
