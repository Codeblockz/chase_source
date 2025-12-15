"""
Source comparison node.
"""

import json
import logging

from openai import OpenAI

from config import settings
from prompts.templates import SOURCE_ATTRIBUTION_SYSTEM, SOURCE_ATTRIBUTION_USER
from schemas.models import Evidence, EvidenceAssessment, GraphState

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def classify_source_attribution(
    claim: str, evidence: Evidence
) -> EvidenceAssessment | None:
    """Classify how a single source relates to the claim."""
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SOURCE_ATTRIBUTION_SYSTEM},
                {
                    "role": "user",
                    "content": SOURCE_ATTRIBUTION_USER.format(
                        claim=claim,
                        source_title=evidence.source_title,
                        source_type=evidence.source_type.value,
                        verbatim_quote=evidence.verbatim_quote,
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        return EvidenceAssessment(
            evidence=evidence,
            attribution=result["attribution"],
            reasoning=result["reasoning"],
        )

    except Exception as e:
        logger.warning(f"Source attribution failed: {e}")
        return None


def compare_sources(state: GraphState) -> GraphState:
    """
    Classify how all sources relate to the claim.

    Args:
        state: Current graph state with evidence and extracted_claim

    Returns:
        Updated state with assessments
    """
    claim = state.get("extracted_claim")
    evidence_list = state.get("evidence", [])

    if not claim or not evidence_list:
        logger.warning("No claim or evidence to compare")
        return {**state, "assessments": []}

    claim_text = claim.claim
    assessments = []

    for evidence in evidence_list:
        assessment = classify_source_attribution(claim_text, evidence)
        if assessment:
            assessments.append(assessment)
            logger.info(
                f"Attribution: {evidence.source_title} -> {assessment.attribution}"
            )

    logger.info(f"Completed {len(assessments)} source attributions")
    return {**state, "assessments": assessments}
