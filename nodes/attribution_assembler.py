"""
Attribution assembly node.
"""

import json
import logging

from openai import OpenAI

from config import settings
from prompts.templates import ATTRIBUTION_ASSEMBLY_SYSTEM, ATTRIBUTION_ASSEMBLY_USER
from schemas.models import (
    AttributionType,
    EvidenceAssessment,
    GraphState,
    SourceAttribution,
    SourceType,
)

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def format_assessments_for_prompt(assessments: list[EvidenceAssessment]) -> str:
    """Format source assessments for the attribution prompt."""
    if not assessments:
        return "No relevant sources found."

    lines = []
    for i, a in enumerate(assessments, 1):
        lines.append(
            f"""
Source {i}:
- Title: {a.evidence.source_title}
- Type: {a.evidence.source_type.value}
- Quote: "{a.evidence.verbatim_quote}"
- Attribution: {a.attribution}
- Reasoning: {a.reasoning}
"""
        )
    return "\n".join(lines)


def find_best_source(assessments: list[EvidenceAssessment]) -> EvidenceAssessment | None:
    """Find the best source based on type and attribution."""
    if not assessments:
        return None

    # Priority: primary > original_reporting > secondary
    # Within each, prefer direct > paraphrase
    def score(a: EvidenceAssessment) -> tuple:
        type_score = {
            SourceType.PRIMARY: 3,
            SourceType.ORIGINAL_REPORTING: 2,
            SourceType.SECONDARY: 1,
            SourceType.UNKNOWN: 0,
        }.get(a.evidence.source_type, 0)

        attr_score = {"direct": 2, "paraphrase": 1, "contradiction": 0}.get(
            a.attribution, 0
        )

        return (type_score, attr_score)

    return max(assessments, key=score)


def assemble_attribution(state: GraphState) -> GraphState:
    """
    Assemble final attribution from source assessments.

    Args:
        state: Current graph state with assessments and extracted_claim

    Returns:
        Updated state with final result
    """
    # Handle extraction failure case
    if state.get("extraction_failed", False):
        result = SourceAttribution(
            claim="[No factual claim could be extracted]",
            attribution=AttributionType.NOT_FOUND,
            summary=state.get("extraction_error")
            or "Could not extract a verifiable factual claim from the input.",
            evidence_list=[],
            best_source=None,
            relies_on_secondary_only=False,
        )
        return {**state, "result": result}

    claim = state.get("extracted_claim")
    assessments = state.get("assessments", [])

    # Handle no sources found
    if not assessments:
        result = SourceAttribution(
            claim=claim.claim if claim else "[Unknown]",
            attribution=AttributionType.NOT_FOUND,
            summary="No relevant sources were found that address this claim.",
            evidence_list=[],
            best_source=None,
            relies_on_secondary_only=False,
        )
        return {**state, "result": result}

    # Check if all evidence is secondary
    relies_on_secondary = all(
        a.evidence.source_type == SourceType.SECONDARY for a in assessments
    )

    # Find best source
    best_source = find_best_source(assessments)

    # Format assessments for prompt
    assessments_text = format_assessments_for_prompt(assessments)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": ATTRIBUTION_ASSEMBLY_SYSTEM},
                {
                    "role": "user",
                    "content": ATTRIBUTION_ASSEMBLY_USER.format(
                        claim=claim.claim, source_assessments=assessments_text
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        llm_result = json.loads(response.choices[0].message.content)

        result = SourceAttribution(
            claim=claim.claim,
            attribution=AttributionType(llm_result["attribution"]),
            summary=llm_result["summary"],
            evidence_list=assessments,
            best_source=best_source,
            relies_on_secondary_only=relies_on_secondary
            or llm_result.get("relies_on_secondary_only", False),
        )

        logger.info(f"Final attribution: {result.attribution.value}")
        return {**state, "result": result}

    except Exception as e:
        logger.error(f"Attribution assembly error: {e}")
        result = SourceAttribution(
            claim=claim.claim,
            attribution=AttributionType.NOT_FOUND,
            summary=f"An error occurred while assembling the attribution: {e}",
            evidence_list=assessments,
            best_source=best_source,
            relies_on_secondary_only=relies_on_secondary,
        )
        return {
            **state,
            "result": result,
            "errors": state.get("errors", []) + [f"Attribution assembly: {e}"],
        }
