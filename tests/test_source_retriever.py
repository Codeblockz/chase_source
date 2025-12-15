"""
Unit tests for source retrieval node.
"""

import pytest
from unittest.mock import patch

from nodes.source_retriever import retrieve_sources
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
                "score": 0.85,
            }
        ]

        with patch("nodes.source_retriever.tavily") as mock_tavily:
            mock_tavily.search.return_value = create_mock_tavily_response(mock_results)

            state = {**initial_graph_state, "extracted_claim": sample_extracted_claim}
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

            state = {**initial_graph_state, "extracted_claim": sample_extracted_claim}
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
                "score": 0.9,
            },
        ]

        with patch("nodes.source_retriever.tavily") as mock_tavily:
            mock_tavily.search.return_value = create_mock_tavily_response(mock_results)

            state = {**initial_graph_state, "extracted_claim": sample_extracted_claim}
            result = retrieve_sources(state)

            # Should only have the valid result
            assert len(result["search_results"]) == 1
            assert "good" in str(result["search_results"][0].url)
