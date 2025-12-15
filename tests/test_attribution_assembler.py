"""
Unit tests for attribution assembly node.
"""

import pytest
from unittest.mock import patch

from nodes.attribution_assembler import assemble_attribution
from schemas.models import (
    AttributionAssemblyResponse,
    AttributionType,
    Evidence,
    EvidenceAssessment,
    SourceType,
)


class TestAttributionAssembler:
    """Tests for attribution assembly."""

    @pytest.mark.unit
    def test_assembles_direct_attribution(
        self,
        sample_extracted_claim,
        sample_assessments,
        initial_graph_state,
        mock_assembly_response,
    ):
        """Should produce DIRECT attribution for direct evidence."""
        with patch("nodes.attribution_assembler.chain") as mock_chain:
            mock_chain.invoke.return_value = mock_assembly_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "assessments": sample_assessments,
            }
            result = assemble_attribution(state)

            assert result["result"] is not None
            assert result["result"].attribution == AttributionType.DIRECT

    @pytest.mark.unit
    def test_handles_extraction_failure(self, initial_graph_state):
        """Should return NOT_FOUND attribution for extraction failure."""
        state = {
            **initial_graph_state,
            "extraction_failed": True,
            "extraction_error": "No factual claims found.",
        }
        result = assemble_attribution(state)

        assert result["result"] is not None
        assert result["result"].attribution == AttributionType.NOT_FOUND
        assert "[No factual claim" in result["result"].claim

    @pytest.mark.unit
    def test_handles_no_assessments(
        self, sample_extracted_claim, initial_graph_state
    ):
        """Should return NOT_FOUND when no sources were found."""
        state = {
            **initial_graph_state,
            "extracted_claim": sample_extracted_claim,
            "assessments": [],
        }
        result = assemble_attribution(state)

        assert result["result"] is not None
        assert result["result"].attribution == AttributionType.NOT_FOUND

    @pytest.mark.unit
    def test_detects_secondary_only(
        self, sample_extracted_claim, initial_graph_state
    ):
        """Should flag when attribution relies only on secondary sources."""
        secondary_evidence = Evidence(
            source_url="https://blog.example.com/article",
            source_title="Blog Article",
            source_type=SourceType.SECONDARY,
            verbatim_quote="According to reports, Tesla delivered vehicles.",
            relevance_score=0.7,
            relevance_explanation="Secondary source",
        )
        secondary_assessment = EvidenceAssessment(
            evidence=secondary_evidence,
            attribution="paraphrase",
            reasoning="Blog confirms claim",
        )

        mock_response = AttributionAssemblyResponse(
            attribution="paraphrase",
            summary="Only secondary sources available.",
            relies_on_secondary_only=True,
        )

        with patch("nodes.attribution_assembler.chain") as mock_chain:
            mock_chain.invoke.return_value = mock_response

            state = {
                **initial_graph_state,
                "extracted_claim": sample_extracted_claim,
                "assessments": [secondary_assessment],
            }
            result = assemble_attribution(state)

            assert result["result"].relies_on_secondary_only is True
