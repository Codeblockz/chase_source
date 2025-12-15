"""
Unit tests for evidence filtering node.
"""

import pytest
from unittest.mock import patch

from nodes.evidence_filter import filter_evidence
from schemas.models import (
    EvidenceRelevanceResponse,
    SearchResult,
    SourceClassificationResponse,
)


class TestEvidenceFilter:
    """Tests for evidence filtering."""

    @pytest.mark.unit
    def test_filters_relevant_evidence(
        self,
        sample_extracted_claim,
        sample_search_results,
        initial_graph_state,
        mock_relevance_response,
        mock_classification_response,
    ):
        """Should filter and extract relevant evidence."""
        low_relevance = EvidenceRelevanceResponse(
            is_relevant=False,
            relevance_score=0.2,
            verbatim_quote=None,
            relevance_explanation="Not relevant.",
        )

        with patch("nodes.evidence_filter.relevance_chain") as mock_rel, \
             patch("nodes.evidence_filter.classification_chain") as mock_class:
            # Return different responses for different calls
            mock_rel.invoke.side_effect = [
                mock_relevance_response,
                mock_relevance_response,
                low_relevance,
            ]
            mock_class.invoke.return_value = mock_classification_response

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
        self,
        sample_extracted_claim,
        initial_graph_state,
        mock_relevance_response,
        mock_classification_response,
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

        with patch("nodes.evidence_filter.relevance_chain") as mock_rel, \
             patch("nodes.evidence_filter.classification_chain") as mock_class:
            mock_rel.invoke.return_value = mock_relevance_response
            mock_class.invoke.return_value = mock_classification_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "search_results": many_results,
            }
            result = filter_evidence(state)

            assert len(result["evidence"]) <= 5
