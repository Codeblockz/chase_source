"""
Claim extraction node.
"""

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import settings
from prompts.templates import CLAIM_EXTRACTION_SYSTEM, CLAIM_EXTRACTION_USER
from schemas.models import ClaimExtractionResponse, ExtractedClaim, GraphState

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.0,
    api_key=settings.openai_api_key,
)
structured_llm = llm.with_structured_output(ClaimExtractionResponse)

prompt = ChatPromptTemplate.from_messages([
    ("system", CLAIM_EXTRACTION_SYSTEM),
    ("user", CLAIM_EXTRACTION_USER),
])

chain = prompt | structured_llm


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
        result: ClaimExtractionResponse = chain.invoke({"input_text": input_text})

        if result.extraction_failed:
            logger.warning(f"Extraction failed: {result.extraction_notes}")
            return {
                **state,
                "extracted_claim": None,
                "extraction_failed": True,
                "extraction_error": result.extraction_notes,
            }

        claim = ExtractedClaim(
            claim=result.claim,
            original_context=result.original_context,
            extraction_confidence=result.extraction_confidence,
            extraction_notes=result.extraction_notes,
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
