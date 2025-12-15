"""
Unit tests for source comparison node.
"""

import pytest
from unittest.mock import patch

from nodes.source_comparer import compare_sources
from schemas.models import SourceAttributionResponse


class TestSourceComparer:
    """Tests for source comparison."""

    @pytest.mark.unit
    def test_compares_supporting_evidence(
        self,
        sample_extracted_claim,
        sample_evidence,
        initial_graph_state,
        mock_attribution_response,
    ):
        """Should identify supporting evidence."""
        with patch("nodes.source_comparer.chain") as mock_chain:
            mock_chain.invoke.return_value = mock_attribution_response

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
        contradiction_response = SourceAttributionResponse(
            attribution="contradiction",
            reasoning="Source states different numbers.",
        )

        with patch("nodes.source_comparer.chain") as mock_chain:
            mock_chain.invoke.return_value = contradiction_response

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
