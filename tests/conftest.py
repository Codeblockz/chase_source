"""
Shared pytest fixtures.
"""

import pytest
from unittest.mock import MagicMock, patch

from schemas.models import (
    AttributionType,
    Evidence,
    EvidenceAssessment,
    ExtractedClaim,
    GraphState,
    SearchResult,
    SourceAttribution,
    SourceType,
)


# === Mock API Clients ===


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that returns controllable responses."""
    with patch("nodes.claim_extractor.client") as mock:
        yield mock


@pytest.fixture
def mock_tavily_client():
    """Mock Tavily client that returns controllable responses."""
    with patch("nodes.source_retriever.tavily") as mock:
        yield mock


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


# === Mock Response Helpers ===


def create_mock_openai_response(content: str):
    """Create a mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


def create_mock_tavily_response(results: list[dict]):
    """Create a mock Tavily API response."""
    return {"results": results}
