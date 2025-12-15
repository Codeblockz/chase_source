"""
Unit tests for source comparison node.
"""

import json

import pytest
from unittest.mock import patch

from nodes.source_comparer import compare_sources
from tests.conftest import create_mock_openai_response


class TestSourceComparer:
    """Tests for source comparison."""

    @pytest.mark.unit
    def test_compares_supporting_evidence(
        self, sample_extracted_claim, sample_evidence, initial_graph_state
    ):
        """Should identify supporting evidence."""
        mock_response = create_mock_openai_response(
            json.dumps(
                {
                    "attribution": "direct",
                    "reasoning": "Official source confirms the claim.",
                }
            )
        )

        with patch("nodes.source_comparer.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "evidence": sample_evidence,
            }
            result = compare_sources(state)

            assert len(result["assessments"]) == len(sample_evidence)
            assert all(a.attribution == "direct" for a in result["assessments"])

    @pytest.mark.unit
    def test_compares_contradicting_evidence(
        self, sample_extracted_claim, sample_evidence, initial_graph_state
    ):
        """Should identify contradicting evidence."""
        mock_response = create_mock_openai_response(
            json.dumps(
                {
                    "attribution": "contradiction",
                    "reasoning": "Source states different numbers.",
                }
            )
        )

        with patch("nodes.source_comparer.client") as mock_client:
            mock_client.chat.completions.create.return_value = mock_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "evidence": sample_evidence,
            }
            result = compare_sources(state)

            assert all(
                a.attribution == "contradiction" for a in result["assessments"]
            )

    @pytest.mark.unit
    def test_handles_no_evidence(self, sample_extracted_claim, initial_graph_state):
        """Should return empty assessments if no evidence."""
        state = {
            **initial_graph_state,
            "extracted_claim": sample_extracted_claim,
            "evidence": [],
        }
        result = compare_sources(state)

        assert result["assessments"] == []
