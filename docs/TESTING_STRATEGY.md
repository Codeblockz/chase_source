# Testing Strategy

Test plan and examples for Chase the Source.

---

## Testing Philosophy

1. **Mock external APIs** - Never hit OpenAI/Tavily in unit tests
2. **Deterministic tests** - Same input → same output
3. **Test at boundaries** - Focus on edge cases and error handling
4. **Integration tests** - Verify end-to-end workflow separately

---

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and mocks
├── fixtures/
│   ├── inputs.py                  # Sample input texts
│   ├── claims.py                  # Expected extracted claims
│   ├── search_results.py          # Mock Tavily responses
│   └── evidence.py                # Mock evidence data
├── test_claim_extractor.py        # Claim extraction unit tests
├── test_source_retriever.py       # Source retrieval unit tests
├── test_evidence_filter.py        # Evidence filtering unit tests
├── test_evidence_comparer.py      # Evidence comparison unit tests
├── test_verdict_assembler.py      # Verdict assembly unit tests
├── test_graph.py                  # Workflow integration tests
└── test_app.py                    # Gradio UI tests
```

---

## Configuration

### File: `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests (fast, mocked)
    integration: Integration tests (may use real APIs)
    slow: Slow tests (skip with -m "not slow")
```

### File: `pyproject.toml` (pytest section)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["nodes", "schemas", "prompts"]
omit = ["tests/*", "*/__init__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError"
]
```

---

## Shared Fixtures

### File: `tests/conftest.py`

```python
"""
Shared pytest fixtures.
"""

import pytest
from unittest.mock import MagicMock, patch
from schemas.models import (
    ExtractedClaim, SearchResult, Evidence, EvidenceAssessment,
    Verdict, VerdictType, SourceType, GraphState
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
        extraction_notes=None
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
            raw_content=None
        ),
        SearchResult(
            url="https://reuters.com/business/autos/tesla-deliveries-2023",
            title="Tesla delivers record 1.8 million vehicles in 2023",
            content="Tesla Inc delivered 1.81 million vehicles in 2023, according to figures released Wednesday.",
            score=0.88,
            published_date=None,
            raw_content=None
        ),
        SearchResult(
            url="https://random-blog.com/ev-news",
            title="EV Market Review 2023",
            content="The electric vehicle market saw significant growth in 2023 with various manufacturers competing.",
            score=0.3,
            published_date=None,
            raw_content=None
        )
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
            relevance_explanation="Official Tesla investor relations directly stating delivery numbers."
        ),
        Evidence(
            source_url="https://reuters.com/business/autos/tesla-deliveries-2023",
            source_title="Tesla delivers record 1.8 million vehicles in 2023",
            source_type=SourceType.ORIGINAL_REPORTING,
            verbatim_quote="Tesla Inc delivered 1.81 million vehicles in 2023.",
            relevance_score=0.88,
            relevance_explanation="Reuters original reporting confirming delivery figures."
        )
    ]


@pytest.fixture
def sample_assessments(sample_evidence):
    """Pre-built evidence assessments for downstream tests."""
    return [
        EvidenceAssessment(
            evidence=sample_evidence[0],
            supports_claim="supports",
            reasoning="Official Tesla report confirms 1.81 million deliveries, matching the claim.",
            strength="strong"
        ),
        EvidenceAssessment(
            evidence=sample_evidence[1],
            supports_claim="supports",
            reasoning="Reuters confirms the delivery figure from Tesla.",
            strength="moderate"
        )
    ]


@pytest.fixture
def sample_verdict(sample_assessments):
    """Pre-built verdict for UI tests."""
    return Verdict(
        claim="Tesla delivered approximately 1.81 million vehicles in 2023.",
        verdict=VerdictType.SUPPORTED,
        confidence="high",
        summary="Tesla's official investor relations report confirms delivery of approximately 1.81 million vehicles in 2023, corroborated by major news outlets.",
        evidence_list=sample_assessments,
        relies_on_secondary_only=False,
        caveats=[]
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
        verdict=None,
        errors=[]
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
```

---

## Unit Tests by Node

### File: `tests/test_claim_extractor.py`

```python
"""
Unit tests for claim extraction node.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from nodes.claim_extractor import extract_claim
from schemas.models import GraphState
from tests.conftest import create_mock_openai_response


class TestClaimExtractor:
    """Tests for claim extraction."""

    @pytest.mark.unit
    def test_extracts_factual_claim(self, sample_input_text, initial_graph_state):
        """Should extract a factual claim from text with facts."""
        mock_response = create_mock_openai_response(json.dumps({
            "claim": "Tesla delivered approximately 1.81 million vehicles in 2023.",
            "original_context": "the company delivered approximately 1.81 million vehicles in 2023",
            "extraction_confidence": "high",
            "extraction_notes": None,
            "extraction_failed": False
        }))

        with patch("nodes.claim_extractor.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {**initial_graph_state, "input_text": sample_input_text}
            result = extract_claim(state)

            assert result["extraction_failed"] is False
            assert result["extracted_claim"] is not None
            assert "Tesla" in result["extracted_claim"].claim
            assert result["extracted_claim"].extraction_confidence == "high"

    @pytest.mark.unit
    def test_handles_opinion_only_text(self, sample_opinion_text, initial_graph_state):
        """Should return extraction_failed for opinion-only text."""
        mock_response = create_mock_openai_response(json.dumps({
            "claim": None,
            "original_context": None,
            "extraction_confidence": None,
            "extraction_notes": "No verifiable factual claims found.",
            "extraction_failed": True
        }))

        with patch("nodes.claim_extractor.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {**initial_graph_state, "input_text": sample_opinion_text}
            result = extract_claim(state)

            assert result["extraction_failed"] is True
            assert result["extracted_claim"] is None
            assert result["extraction_error"] is not None

    @pytest.mark.unit
    def test_handles_api_error(self, initial_graph_state):
        """Should gracefully handle API errors."""
        with patch("nodes.claim_extractor.client") as mock_client:
            mock_client.chat.completions.create.side_effect = Exception("API Error")

            state = {**initial_graph_state, "input_text": "Some text"}
            result = extract_claim(state)

            assert result["extraction_failed"] is True
            assert "API Error" in result["extraction_error"]
            assert len(result["errors"]) > 0

    @pytest.mark.unit
    def test_handles_malformed_json(self, initial_graph_state):
        """Should handle malformed JSON from API."""
        mock_response = create_mock_openai_response("not valid json")

        with patch("nodes.claim_extractor.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {**initial_graph_state, "input_text": "Some text"}
            result = extract_claim(state)

            assert result["extraction_failed"] is True
```

---

### File: `tests/test_source_retriever.py`

```python
"""
Unit tests for source retrieval node.
"""

import pytest
from unittest.mock import patch
from nodes.source_retriever import retrieve_sources
from schemas.models import GraphState
from tests.conftest import create_mock_tavily_response


class TestSourceRetriever:
    """Tests for source retrieval."""

    @pytest.mark.unit
    def test_retrieves_sources_for_claim(
        self, sample_extracted_claim, initial_graph_state
    ):
        """Should retrieve sources from Tavily for valid claim."""
        mock_results = [
            {
                "url": "https://example.com/article",
                "title": "Test Article",
                "content": "Test content about the claim.",
                "score": 0.85
            }
        ]

        with patch("nodes.source_retriever.tavily") as mock_tavily:
            mock_tavily.search.return_value = create_mock_tavily_response(mock_results)

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim
            }
            result = retrieve_sources(state)

            assert len(result["search_results"]) == 1
            assert result["search_query"] == sample_extracted_claim.claim
            mock_tavily.search.assert_called_once()

    @pytest.mark.unit
    def test_handles_no_claim(self, initial_graph_state):
        """Should return empty results if no claim provided."""
        state = {**initial_graph_state, "extracted_claim": None}
        result = retrieve_sources(state)

        assert result["search_results"] == []
        assert result["search_query"] is None

    @pytest.mark.unit
    def test_handles_tavily_error(self, sample_extracted_claim, initial_graph_state):
        """Should gracefully handle Tavily API errors."""
        with patch("nodes.source_retriever.tavily") as mock_tavily:
            mock_tavily.search.side_effect = Exception("Tavily Error")

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim
            }
            result = retrieve_sources(state)

            assert result["search_results"] == []
            assert len(result["errors"]) > 0

    @pytest.mark.unit
    def test_filters_malformed_results(
        self, sample_extracted_claim, initial_graph_state
    ):
        """Should skip malformed search results."""
        mock_results = [
            {"url": "not-a-valid-url", "title": "Bad"},  # Invalid URL
            {
                "url": "https://example.com/good",
                "title": "Good Article",
                "content": "Good content",
                "score": 0.9
            }
        ]

        with patch("nodes.source_retriever.tavily") as mock_tavily:
            mock_tavily.search.return_value = create_mock_tavily_response(mock_results)

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim
            }
            result = retrieve_sources(state)

            # Should only have the valid result
            assert len(result["search_results"]) == 1
            assert "good" in str(result["search_results"][0].url)
```

---

### File: `tests/test_evidence_filter.py`

```python
"""
Unit tests for evidence filtering node.
"""

import pytest
import json
from unittest.mock import patch
from nodes.evidence_filter import filter_evidence
from schemas.models import GraphState, SourceType
from tests.conftest import create_mock_openai_response


class TestEvidenceFilter:
    """Tests for evidence filtering."""

    @pytest.mark.unit
    def test_filters_relevant_evidence(
        self, sample_extracted_claim, sample_search_results, initial_graph_state
    ):
        """Should filter and extract relevant evidence."""
        # Mock relevance assessment - high relevance
        relevance_response = create_mock_openai_response(json.dumps({
            "is_relevant": True,
            "relevance_score": 0.95,
            "verbatim_quote": "Tesla delivered approximately 1.81 million vehicles.",
            "relevance_explanation": "Direct statement of delivery numbers."
        }))

        # Mock source classification
        classification_response = create_mock_openai_response(json.dumps({
            "source_type": "primary",
            "reasoning": "Official Tesla source"
        }))

        with patch("nodes.evidence_filter.client") as mock_client:
            # Return different responses for different calls
            mock_client.chat.completions.create.side_effect = [
                relevance_response,
                classification_response,
                # For second result
                relevance_response,
                classification_response,
                # For third result (low relevance)
                create_mock_openai_response(json.dumps({
                    "is_relevant": False,
                    "relevance_score": 0.2,
                    "verbatim_quote": None,
                    "relevance_explanation": "Not relevant."
                }))
            ]

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "search_results": sample_search_results
            }
            result = filter_evidence(state)

            # Should have 2 relevant results (third filtered out)
            assert len(result["evidence"]) == 2
            assert all(e.relevance_score >= 0.5 for e in result["evidence"])

    @pytest.mark.unit
    def test_handles_no_search_results(
        self, sample_extracted_claim, initial_graph_state
    ):
        """Should return empty evidence if no search results."""
        state = {
            **initial_graph_state,
            "extracted_claim": sample_extracted_claim,
            "search_results": []
        }
        result = filter_evidence(state)

        assert result["evidence"] == []

    @pytest.mark.unit
    def test_limits_to_five_evidence_items(
        self, sample_extracted_claim, initial_graph_state
    ):
        """Should limit evidence to maximum 5 items."""
        # Create 10 search results
        many_results = []
        for i in range(10):
            from schemas.models import SearchResult
            many_results.append(SearchResult(
                url=f"https://example{i}.com/article",
                title=f"Article {i}",
                content=f"Content about the claim {i}",
                score=0.9
            ))

        relevance_response = create_mock_openai_response(json.dumps({
            "is_relevant": True,
            "relevance_score": 0.9,
            "verbatim_quote": "Relevant quote.",
            "relevance_explanation": "Relevant."
        }))
        classification_response = create_mock_openai_response(json.dumps({
            "source_type": "secondary",
            "reasoning": "News article"
        }))

        with patch("nodes.evidence_filter.client") as mock_client:
            # All results are relevant
            mock_client.chat.completions.create.return_value = relevance_response
            mock_client.chat.completions.create.side_effect = None
            # Alternate between relevance and classification responses
            responses = []
            for _ in range(10):
                responses.extend([relevance_response, classification_response])
            mock_client.chat.completions.create.side_effect = responses

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "search_results": many_results
            }
            result = filter_evidence(state)

            assert len(result["evidence"]) <= 5
```

---

### File: `tests/test_evidence_comparer.py`

```python
"""
Unit tests for evidence comparison node.
"""

import pytest
import json
from unittest.mock import patch
from nodes.evidence_comparer import compare_evidence
from schemas.models import GraphState
from tests.conftest import create_mock_openai_response


class TestEvidenceComparer:
    """Tests for evidence comparison."""

    @pytest.mark.unit
    def test_compares_supporting_evidence(
        self, sample_extracted_claim, sample_evidence, initial_graph_state
    ):
        """Should identify supporting evidence."""
        mock_response = create_mock_openai_response(json.dumps({
            "supports_claim": "supports",
            "strength": "strong",
            "reasoning": "Official source confirms the claim."
        }))

        with patch("nodes.evidence_comparer.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "evidence": sample_evidence
            }
            result = compare_evidence(state)

            assert len(result["assessments"]) == len(sample_evidence)
            assert all(a.supports_claim == "supports" for a in result["assessments"])

    @pytest.mark.unit
    def test_compares_contradicting_evidence(
        self, sample_extracted_claim, sample_evidence, initial_graph_state
    ):
        """Should identify contradicting evidence."""
        mock_response = create_mock_openai_response(json.dumps({
            "supports_claim": "contradicts",
            "strength": "strong",
            "reasoning": "Source states different numbers."
        }))

        with patch("nodes.evidence_comparer.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "evidence": sample_evidence
            }
            result = compare_evidence(state)

            assert all(a.supports_claim == "contradicts" for a in result["assessments"])

    @pytest.mark.unit
    def test_handles_no_evidence(self, sample_extracted_claim, initial_graph_state):
        """Should return empty assessments if no evidence."""
        state = {
            **initial_graph_state,
            "extracted_claim": sample_extracted_claim,
            "evidence": []
        }
        result = compare_evidence(state)

        assert result["assessments"] == []
```

---

### File: `tests/test_verdict_assembler.py`

```python
"""
Unit tests for verdict assembly node.
"""

import pytest
import json
from unittest.mock import patch
from nodes.verdict_assembler import assemble_verdict
from schemas.models import GraphState, VerdictType
from tests.conftest import create_mock_openai_response


class TestVerdictAssembler:
    """Tests for verdict assembly."""

    @pytest.mark.unit
    def test_assembles_supported_verdict(
        self, sample_extracted_claim, sample_assessments, initial_graph_state
    ):
        """Should produce SUPPORTED verdict for supporting evidence."""
        mock_response = create_mock_openai_response(json.dumps({
            "verdict": "supported",
            "confidence": "high",
            "summary": "Evidence supports the claim.",
            "relies_on_secondary_only": False,
            "caveats": []
        }))

        with patch("nodes.verdict_assembler.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "assessments": sample_assessments
            }
            result = assemble_verdict(state)

            assert result["verdict"] is not None
            assert result["verdict"].verdict == VerdictType.SUPPORTED
            assert result["verdict"].confidence == "high"

    @pytest.mark.unit
    def test_handles_extraction_failure(self, initial_graph_state):
        """Should return UNCLEAR verdict for extraction failure."""
        state = {
            **initial_graph_state,
            "extraction_failed": True,
            "extraction_error": "No factual claims found."
        }
        result = assemble_verdict(state)

        assert result["verdict"] is not None
        assert result["verdict"].verdict == VerdictType.UNCLEAR
        assert "No factual claim" in result["verdict"].caveats[0]

    @pytest.mark.unit
    def test_detects_secondary_only(
        self, sample_extracted_claim, initial_graph_state
    ):
        """Should flag when verdict relies only on secondary sources."""
        from schemas.models import Evidence, EvidenceAssessment, SourceType

        secondary_evidence = Evidence(
            source_url="https://blog.example.com/article",
            source_title="Blog Article",
            source_type=SourceType.SECONDARY,
            verbatim_quote="According to reports...",
            relevance_score=0.7,
            relevance_explanation="Secondary source"
        )
        secondary_assessment = EvidenceAssessment(
            evidence=secondary_evidence,
            supports_claim="supports",
            reasoning="Blog confirms claim",
            strength="weak"
        )

        mock_response = create_mock_openai_response(json.dumps({
            "verdict": "unclear",
            "confidence": "low",
            "summary": "Only secondary sources available.",
            "relies_on_secondary_only": True,
            "caveats": ["No primary sources"]
        }))

        with patch("nodes.verdict_assembler.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "assessments": [secondary_assessment]
            }
            result = assemble_verdict(state)

            assert result["verdict"].relies_on_secondary_only is True
```

---

## Integration Tests

### File: `tests/test_graph.py`

```python
"""
Integration tests for the full LangGraph workflow.
"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestGraphIntegration:
    """Integration tests for full pipeline."""

    @pytest.mark.integration
    def test_full_pipeline_supported_claim(self, sample_input_text):
        """Test complete pipeline with a supportable claim."""
        # This test requires more elaborate mocking of the entire pipeline
        # For true integration testing, you might use a separate test environment
        pass  # Implement with full mock chain

    @pytest.mark.integration
    def test_full_pipeline_opinion_text(self, sample_opinion_text):
        """Test pipeline handles opinion-only text correctly."""
        pass  # Implement with full mock chain

    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_pipeline_real_apis(self):
        """
        Test with real APIs (requires valid API keys).

        Run with: pytest -m "integration and slow" --real-apis
        """
        pytest.skip("Requires --real-apis flag and valid API keys")
```

---

## Running Tests

### Commands

```bash
# Run all unit tests
pytest -m unit

# Run all tests with coverage
pytest --cov=nodes --cov=schemas --cov-report=html

# Run specific test file
pytest tests/test_claim_extractor.py -v

# Run tests matching pattern
pytest -k "test_extract" -v

# Run with verbose output
pytest -v --tb=long

# Skip slow tests
pytest -m "not slow"

# Run integration tests only
pytest -m integration
```

### Coverage Target

| Module | Target Coverage |
|--------|-----------------|
| nodes/ | 80% |
| schemas/ | 90% |
| prompts/ | N/A (constants) |
| graph.py | 70% |
| app.py | 60% |

---

## Test Fixtures Reference

### File: `tests/fixtures/inputs.py`

```python
"""
Sample input texts for testing.
"""

# Clear factual claim
FACTUAL_INPUT = """
According to Tesla's Q4 2023 report, the company delivered approximately
1.81 million vehicles in 2023, a 38% increase year-over-year.
"""

# Opinion only
OPINION_INPUT = """
Tesla is the best car company ever. Elon Musk is a genius and the stock
is definitely going to $1000. Anyone who disagrees is wrong.
"""

# Mixed content
MIXED_INPUT = """
I think Tesla is overvalued, but they did report record deliveries of
1.81 million vehicles last year. Still, the stock price is too high.
"""

# Compound claims
COMPOUND_INPUT = """
Tesla delivered 1.81 million vehicles AND increased production by 35%
while also expanding into new markets across Asia.
"""

# Historical claim
HISTORICAL_INPUT = """
In 1969, Neil Armstrong became the first human to walk on the moon as
part of NASA's Apollo 11 mission.
"""

# Unverifiable claim
UNVERIFIABLE_INPUT = """
Sources say the company is planning a major announcement next month that
will revolutionize the industry. Multiple insiders confirm this.
"""

# Empty and edge cases
EMPTY_INPUT = ""
WHITESPACE_INPUT = "   \n\t   "
SHORT_INPUT = "Tesla."
VERY_LONG_INPUT = "Tesla " * 1000
```

---

## CI/CD Considerations

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run unit tests
        run: pytest -m unit --cov=nodes --cov=schemas

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

---

## Mocking Best Practices

1. **Mock at the boundary** - Mock API clients, not internal functions
2. **Use fixtures** - Share test data via pytest fixtures
3. **Explicit assertions** - Assert specific values, not just "not None"
4. **Test error paths** - Verify graceful degradation
5. **Avoid over-mocking** - Let real code run where possible
