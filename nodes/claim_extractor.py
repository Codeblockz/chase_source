"""
Claim extraction node.
"""

import json
import logging

from openai import OpenAI

from config import settings
from prompts.templates import CLAIM_EXTRACTION_SYSTEM, CLAIM_EXTRACTION_USER
from schemas.models import ExtractedClaim, GraphState

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def extract_claim(state: GraphState) -> GraphState:
    """
    Extract a factual claim from input text.

    Args:
        state: Current graph state with input_text

    Returns:
        Updated state with extracted_claim or extraction_failed
    """
    input_text = state["input_text"]
    logger.info(f"Extracting claim from {len(input_text)} chars")

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": CLAIM_EXTRACTION_SYSTEM},
                {
                    "role": "user",
                    "content": CLAIM_EXTRACTION_USER.format(input_text=input_text),
                },
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        if result.get("extraction_failed", False):
            logger.warning(f"Extraction failed: {result.get('extraction_notes')}")
            return {
                **state,
                "extracted_claim": None,
                "extraction_failed": True,
                "extraction_error": result.get("extraction_notes"),
            }

        claim = ExtractedClaim(
            claim=result["claim"],
            original_context=result["original_context"],
            extraction_confidence=result["extraction_confidence"],
            extraction_notes=result.get("extraction_notes"),
        )

        logger.info(f"Extracted claim: {claim.claim}")
        return {
            **state,
            "extracted_claim": claim,
            "extraction_failed": False,
            "extraction_error": None,
        }

    except Exception as e:
        logger.error(f"Claim extraction error: {e}")
        return {
            **state,
            "extracted_claim": None,
            "extraction_failed": True,
            "extraction_error": str(e),
            "errors": state.get("errors", []) + [f"Claim extraction: {e}"],
        }
