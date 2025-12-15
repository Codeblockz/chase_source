"""
Unit tests for evidence filtering node.
"""

import json

import pytest
from unittest.mock import patch

from nodes.evidence_filter import filter_evidence
from schemas.models import SearchResult
from tests.conftest import create_mock_openai_response


class TestEvidenceFilter:
    """Tests for evidence filtering."""

    @pytest.mark.unit
    def test_filters_relevant_evidence(
        self, sample_extracted_claim, sample_search_results, initial_graph_state
    ):
        """Should filter and extract relevant evidence."""
        # Mock relevance assessment - high relevance
        relevance_response = create_mock_openai_response(
            json.dumps(
                {
                    "is_relevant": True,
                    "relevance_score": 0.95,
                    "verbatim_quote": "Tesla delivered approximately 1.81 million vehicles.",
                    "relevance_explanation": "Direct statement of delivery numbers.",
                }
            )
        )

        # Mock source classification
        classification_response = create_mock_openai_response(
            json.dumps({"source_type": "primary", "reasoning": "Official Tesla source"})
        )

        # Low relevance response
        low_relevance_response = create_mock_openai_response(
            json.dumps(
                {
                    "is_relevant": False,
                    "relevance_score": 0.2,
                    "verbatim_quote": None,
                    "relevance_explanation": "Not relevant.",
                }
            )
        )

        with patch("nodes.evidence_filter.client") as mock_client:
            # Return different responses for different calls
            mock_client.chat.completions.create.side_effect = [
                relevance_response,
                classification_response,
                # For second result
                relevance_response,
                classification_response,
                # For third result (low relevance)
                low_relevance_response,
            ]

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "search_results": sample_search_results,
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
            "search_results": [],
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
            many_results.append(
                SearchResult(
                    url=f"https://example{i}.com/article",
                    title=f"Article {i}",
                    content=f"Content about the claim {i}",
                    score=0.9,
                )
            )

        relevance_response = create_mock_openai_response(
            json.dumps(
                {
                    "is_relevant": True,
                    "relevance_score": 0.9,
                    "verbatim_quote": "Relevant quote about deliveries.",
                    "relevance_explanation": "Relevant.",
                }
            )
        )
        classification_response = create_mock_openai_response(
            json.dumps({"source_type": "secondary", "reasoning": "News article"})
        )

        with patch("nodes.evidence_filter.client") as mock_client:
            # Alternate between relevance and classification responses
            responses = []
            for _ in range(10):
                responses.extend([relevance_response, classification_response])
            mock_client.chat.completions.create.side_effect = responses

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "search_results": many_results,
            }
            result = filter_evidence(state)

            assert len(result["evidence"]) <= 5
