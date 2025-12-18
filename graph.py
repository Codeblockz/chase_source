"""
LangGraph workflow for Chase the Source.
"""

from langgraph.graph import END, StateGraph

from nodes.attribution_assembler import assemble_attribution
from nodes.claim_extractor import extract_claim
from nodes.evidence_filter import filter_evidence
from nodes.source_comparer import compare_sources
from nodes.source_retriever import retrieve_sources
from schemas.models import GraphState


def should_continue_after_extraction(state: GraphState) -> str:
    """Route based on extraction success."""
    if state.get("extraction_failed", False):
        return "attribution_assembler"  # Skip to result with failure
    return "source_retriever"


def build_graph() -> StateGraph:
    """Build and compile the source attribution workflow."""

    # Initialize graph with state schema
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("claim_extractor", extract_claim)
    workflow.add_node("source_retriever", retrieve_sources)
    workflow.add_node("evidence_filter", filter_evidence)
    workflow.add_node("source_comparer", compare_sources)
    workflow.add_node("attribution_assembler", assemble_attribution)

    # Set entry point
    workflow.set_entry_point("claim_extractor")

    # Add edges
    workflow.add_conditional_edges(
        "claim_extractor",
        should_continue_after_extraction,
        {
            "source_retriever": "source_retriever",
            "attribution_assembler": "attribution_assembler",
        },
    )
    workflow.add_edge("source_retriever", "evidence_filter")
    workflow.add_edge("evidence_filter", "source_comparer")
    workflow.add_edge("source_comparer", "attribution_assembler")
    workflow.add_edge("attribution_assembler", END)

    # Compile
    return workflow.compile()


# Singleton graph instance
graph = build_graph()


def run_source_check(input_text: str, input_source_url: str | None = None) -> GraphState:
    """Execute the source attribution pipeline."""
    initial_state: GraphState = {
        "input_text": input_text,
        "input_source_url": input_source_url,
        "extracted_claim": None,
        "extraction_failed": False,
        "extraction_error": None,
        "search_results": [],
        "search_query": None,
        "evidence": [],
        "assessments": [],
        "result": None,
        "errors": [],
    }

    result = graph.invoke(initial_state)
    return result
