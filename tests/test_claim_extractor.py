"""
Unit tests for claim extraction node.
"""

import json

import pytest
from unittest.mock import patch

from nodes.claim_extractor import extract_claim
from tests.conftest import create_mock_openai_response


class TestClaimExtractor:
    """Tests for claim extraction."""

    @pytest.mark.unit
    def test_extracts_factual_claim(self, sample_input_text, initial_graph_state):
        """Should extract a factual claim from text with facts."""
        mock_response = create_mock_openai_response(
            json.dumps(
                {
                    "claim": "Tesla delivered approximately 1.81 million vehicles in 2023.",
                    "original_context": "the company delivered approximately 1.81 million vehicles in 2023",
                    "extraction_confidence": "high",
                    "extraction_notes": None,
                    "extraction_failed": False,
                }
            )
        )

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
        mock_response = create_mock_openai_response(
            json.dumps(
                {
                    "claim": None,
                    "original_context": None,
                    "extraction_confidence": None,
                    "extraction_notes": "No verifiable factual claims found.",
                    "extraction_failed": True,
                }
            )
        )

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
