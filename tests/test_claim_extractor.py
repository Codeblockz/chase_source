"""
Unit tests for claim extraction node.
"""

import pytest
from unittest.mock import patch

from nodes.claim_extractor import extract_claim
from schemas.models import ClaimExtractionResponse


class TestClaimExtractor:
    """Tests for claim extraction."""

    @pytest.mark.unit
    def test_extracts_factual_claim(
        self, sample_input_text, initial_graph_state, mock_claim_extraction_success
    ):
        """Should extract a factual claim from text with facts."""
        with patch("nodes.claim_extractor.chain") as mock_chain:
            mock_chain.invoke.return_value = mock_claim_extraction_success

            state = {**initial_graph_state, "input_text": sample_input_text}
            result = extract_claim(state)

            assert result["extraction_failed"] is False
            assert result["extracted_claim"] is not None
            assert "Tesla" in result["extracted_claim"].claim
            assert result["extracted_claim"].extraction_confidence == "high"

    @pytest.mark.unit
    def test_handles_opinion_only_text(
        self, sample_opinion_text, initial_graph_state, mock_claim_extraction_failed
    ):
        """Should return extraction_failed for opinion-only text."""
        with patch("nodes.claim_extractor.chain") as mock_chain:
            mock_chain.invoke.return_value = mock_claim_extraction_failed

            state = {**initial_graph_state, "input_text": sample_opinion_text}
            result = extract_claim(state)

            assert result["extraction_failed"] is True
            assert result["extracted_claim"] is None
            assert result["extraction_error"] is not None

    @pytest.mark.unit
    def test_handles_api_error(self, initial_graph_state):
        """Should gracefully handle API errors."""
        with patch("nodes.claim_extractor.chain") as mock_chain:
            mock_chain.invoke.side_effect = Exception("API Error")

            state = {**initial_graph_state, "input_text": "Some text"}
            result = extract_claim(state)

            assert result["extraction_failed"] is True
            assert "API Error" in result["extraction_error"]
            assert len(result["errors"]) > 0

    @pytest.mark.unit
    def test_handles_malformed_response(self, initial_graph_state):
        """Should handle unexpected response from chain."""
        with patch("nodes.claim_extractor.chain") as mock_chain:
            mock_chain.invoke.side_effect = Exception("Validation error")

            state = {**initial_graph_state, "input_text": "Some text"}
            result = extract_claim(state)

            assert result["extraction_failed"] is True
