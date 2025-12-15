"""
Shared pytest fixtures.
"""

import pytest
from unittest.mock import MagicMock, patch

from schemas.models import (
    AttributionAssemblyResponse,
    AttributionType,
    ClaimExtractionResponse,
    Evidence,
    EvidenceAssessment,
    EvidenceRelevanceResponse,
    ExtractedClaim,
    GraphState,
    SearchResult,
    SourceAttribution,
    SourceAttributionResponse,
    SourceClassificationResponse,
    SourceType,
)


# === Sample Data Fixtures ===


@pytest.fixture
def sample_input_text():
    """Sample input with a clear factual claim."""
    return """
    According to Tesla's latest earnings report, the company delivered
    approximately 1.81 million vehicles in 2023, representing a 38%
    increase from the previous year.
    """


@pytest.fixture
def sample_opinion_text():
    """Sample input with only opinions, no factual claims."""
    return """
    Tesla is clearly the best electric vehicle company in the world.
    Their cars are amazing and Elon Musk is a genius. The stock is
    definitely going to the moon!
    """


@pytest.fixture
def sample_extracted_claim():
    """Pre-built extracted claim for downstream tests."""
    return ExtractedClaim(
        claim="Tesla delivered approximately 1.81 million vehicles in 2023.",
        original_context="the company delivered approximately 1.81 million vehicles in 2023",
        extraction_confidence="high",
        extraction_notes=None,
    )


@pytest.fixture
def sample_search_results():
    """Mock Tavily search results."""
    return [
        SearchResult(
            url="https://ir.tesla.com/press-release/q4-2023",
            title="Tesla Q4 2023 Update",
            content="In 2023, Tesla produced over 1.84 million vehicles and delivered approximately 1.81 million vehicles.",
            score=0.95,
            published_date=None,
            raw_content=None,
        ),
        SearchResult(
            url="https://reuters.com/business/autos/tesla-deliveries-2023",
            title="Tesla delivers record 1.8 million vehicles in 2023",
            content="Tesla Inc delivered 1.81 million vehicles in 2023, according to figures released Wednesday.",
            score=0.88,
            published_date=None,
            raw_content=None,
        ),
        SearchResult(
            url="https://random-blog.com/ev-news",
            title="EV Market Review 2023",
            content="The electric vehicle market saw significant growth in 2023 with various manufacturers competing.",
            score=0.3,
            published_date=None,
            raw_content=None,
        ),
    ]


@pytest.fixture
def sample_evidence():
    """Pre-built evidence items for downstream tests."""
    return [
        Evidence(
            source_url="https://ir.tesla.com/press-release/q4-2023",
            source_title="Tesla Q4 2023 Update",
            source_type=SourceType.PRIMARY,
            verbatim_quote="In 2023, Tesla produced over 1.84 million vehicles and delivered approximately 1.81 million vehicles.",
            relevance_score=0.95,
            relevance_explanation="Official Tesla investor relations directly stating delivery numbers.",
        ),
        Evidence(
            source_url="https://reuters.com/business/autos/tesla-deliveries-2023",
            source_title="Tesla delivers record 1.8 million vehicles in 2023",
            source_type=SourceType.ORIGINAL_REPORTING,
            verbatim_quote="Tesla Inc delivered 1.81 million vehicles in 2023.",
            relevance_score=0.88,
            relevance_explanation="Reuters original reporting confirming delivery figures.",
        ),
    ]


@pytest.fixture
def sample_assessments(sample_evidence):
    """Pre-built evidence assessments for downstream tests."""
    return [
        EvidenceAssessment(
            evidence=sample_evidence[0],
            attribution="direct",
            reasoning="Official Tesla report confirms 1.81 million deliveries, matching the claim.",
        ),
        EvidenceAssessment(
            evidence=sample_evidence[1],
            attribution="direct",
            reasoning="Reuters confirms the delivery figure from Tesla.",
        ),
    ]


@pytest.fixture
def sample_attribution(sample_assessments):
    """Pre-built attribution for UI tests."""
    return SourceAttribution(
        claim="Tesla delivered approximately 1.81 million vehicles in 2023.",
        attribution=AttributionType.DIRECT,
        summary="Tesla's official investor relations report confirms delivery of approximately 1.81 million vehicles in 2023, corroborated by major news outlets.",
        evidence_list=sample_assessments,
        best_source=sample_assessments[0],
        relies_on_secondary_only=False,
    )


@pytest.fixture
def initial_graph_state():
    """Empty initial graph state."""
    return GraphState(
        input_text="",
        extracted_claim=None,
        extraction_failed=False,
        extraction_error=None,
        search_results=[],
        search_query=None,
        evidence=[],
        assessments=[],
        result=None,
        errors=[],
    )


# === Mock Response Fixtures ===


@pytest.fixture
def mock_claim_extraction_success():
    """Mock successful claim extraction response."""
    return ClaimExtractionResponse(
        claim="Tesla delivered approximately 1.81 million vehicles in 2023.",
        original_context="the company delivered approximately 1.81 million vehicles in 2023",
        extraction_confidence="high",
        extraction_notes=None,
        extraction_failed=False,
    )


@pytest.fixture
def mock_claim_extraction_failed():
    """Mock failed claim extraction response."""
    return ClaimExtractionResponse(
        claim=None,
        original_context=None,
        extraction_confidence=None,
        extraction_notes="No verifiable factual claims found.",
        extraction_failed=True,
    )


@pytest.fixture
def mock_relevance_response():
    """Mock relevance assessment response."""
    return EvidenceRelevanceResponse(
        is_relevant=True,
        relevance_score=0.95,
        verbatim_quote="Tesla delivered approximately 1.81 million vehicles.",
        relevance_explanation="Direct statement of delivery numbers.",
    )


@pytest.fixture
def mock_classification_response():
    """Mock source classification response."""
    return SourceClassificationResponse(
        source_type="primary",
        reasoning="Official Tesla source",
    )


@pytest.fixture
def mock_attribution_response():
    """Mock source attribution response."""
    return SourceAttributionResponse(
        attribution="direct",
        reasoning="Official source confirms the claim.",
    )


@pytest.fixture
def mock_assembly_response():
    """Mock attribution assembly response."""
    return AttributionAssemblyResponse(
        attribution="direct",
        summary="Evidence directly supports the claim.",
        relies_on_secondary_only=False,
    )


# === Mock Tavily Response Helper ===


def create_mock_tavily_response(results: list[dict]):
    """Create a mock Tavily API response."""
    return {"results": results}
