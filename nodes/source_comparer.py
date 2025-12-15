"""
Source comparison node with parallel processing.
"""

import asyncio
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import settings
from prompts.templates import SOURCE_ATTRIBUTION_SYSTEM, SOURCE_ATTRIBUTION_USER
from schemas.models import (
    Evidence,
    EvidenceAssessment,
    GraphState,
    SourceAttributionResponse,
)

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.0,
    api_key=settings.openai_api_key,
)
structured_llm = llm.with_structured_output(SourceAttributionResponse)

prompt = ChatPromptTemplate.from_messages([
    ("system", SOURCE_ATTRIBUTION_SYSTEM),
    ("user", SOURCE_ATTRIBUTION_USER),
])

chain = prompt | structured_llm


async def classify_source_attribution_async(
    claim: str, evidence: Evidence
) -> EvidenceAssessment | None:
    """Classify how a single source relates to the claim (async)."""
    try:
        result: SourceAttributionResponse = await chain.ainvoke({
            "claim": claim,
            "source_title": evidence.source_title,
            "source_type": evidence.source_type.value,
            "verbatim_quote": evidence.verbatim_quote,
        })

        assessment = EvidenceAssessment(
            evidence=evidence,
            attribution=result.attribution,
            reasoning=result.reasoning,
        )
        logger.info(f"Attribution: {evidence.source_title} -> {result.attribution}")
        return assessment

    except Exception as e:
        logger.warning(f"Source attribution failed: {e}")
        return None


async def compare_sources_async(state: GraphState) -> GraphState:
    """Classify how all sources relate to the claim using parallel processing."""
    claim = state.get("extracted_claim")
    evidence_list = state.get("evidence", [])

    if not claim or not evidence_list:
        logger.warning("No claim or evidence to compare")
        return {**state, "assessments": []}

    claim_text = claim.claim

    # Process all evidence in parallel
    tasks = [
        classify_source_attribution_async(claim_text, evidence)
        for evidence in evidence_list
    ]
    assessment_results = await asyncio.gather(*tasks)

    # Filter out None results
    assessments = [a for a in assessment_results if a is not None]

    logger.info(f"Completed {len(assessments)} source attributions")
    return {**state, "assessments": assessments}


def compare_sources(state: GraphState) -> GraphState:
    """
    Classify how all sources relate to the claim.

    Args:
        state: Current graph state with evidence and extracted_claim

    Returns:
        Updated state with assessments
    """
    return asyncio.run(compare_sources_async(state))
