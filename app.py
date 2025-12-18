"""
Gradio UI for Chase the Source.
"""

import logging

import gradio as gr

from config import settings
from graph import run_source_check
from schemas.models import AttributionType, SourceAttribution, SourceType

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def format_attribution_output(result: SourceAttribution) -> tuple[str, str, str]:
    """Format attribution result for display in Gradio."""

    # Claim display
    claim_text = f"**Extracted Claim:**\n\n{result.claim}"

    # Attribution display with color coding
    attribution_colors = {
        AttributionType.DIRECT: "🟢",
        AttributionType.PARAPHRASE: "🟡",
        AttributionType.CONTRADICTION: "🔴",
        AttributionType.NOT_FOUND: "⚪",
    }
    attribution_text = f"""**Attribution:** {attribution_colors.get(result.attribution, "")} {result.attribution.value.upper()}

**Summary:**
{result.summary}
"""

    if result.relies_on_secondary_only:
        attribution_text += "\n⚠️ *This result relies only on secondary reporting.*"

    # Best source highlight
    if result.best_source:
        best = result.best_source
        attribution_text += f"\n\n**Best Source:** {best.evidence.source_title} ({best.evidence.source_type.value})"

    # Sources display
    sources_text = ""
    if result.evidence_list:
        for i, assessment in enumerate(result.evidence_list, 1):
            e = assessment.evidence
            source_type_label = {
                SourceType.PRIMARY: "📋 Primary",
                SourceType.ORIGINAL_REPORTING: "📰 Original Reporting",
                SourceType.SECONDARY: "🔄 Secondary",
                SourceType.UNKNOWN: "❓ Unknown",
            }.get(e.source_type, "Unknown")

            attribution_emoji = {
                "direct": "🎯",
                "paraphrase": "📝",
                "contradiction": "❌",
            }.get(assessment.attribution, "")

            sources_text += f"""
---
### Source {i}: {e.source_title}

**Source Type:** {source_type_label}
**URL:** [{e.source_url}]({e.source_url})

**Quote:**
> {e.verbatim_quote}

**Attribution:** {attribution_emoji} {assessment.attribution}

**Reasoning:** {assessment.reasoning}
"""
    else:
        sources_text = "*No relevant sources found.*"

    return claim_text, attribution_text, sources_text


def process_input(text: str, source_url: str | None = None) -> tuple[str, str, str]:
    """
    Process user input through the source attribution pipeline.

    Args:
        text: User-provided text to analyze
        source_url: Optional URL of the page the text came from (to avoid self-sourcing)

    Returns:
        Tuple of (claim, attribution, sources) formatted strings
    """
    if not text or len(text.strip()) < 10:
        return ("**Error:** Please provide at least 10 characters of text.", "", "")

    logger.info(f"Processing input: {len(text)} characters; source_url provided={bool(source_url)}")

    try:
        result = run_source_check(text, source_url)
        attribution = result.get("result")

        if not attribution:
            return ("**Error:** Failed to produce a result.", "", "")

        return format_attribution_output(attribution)

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return (f"**Error:** An error occurred during processing: {e}", "", "")


# Build Gradio interface
with gr.Blocks(title="Chase the Source", theme=gr.themes.Soft()) as app:
    gr.Markdown(
        """
    # 🔍 Chase the Source

    Paste an article excerpt, social post, or commentary below.
    The system will extract a factual claim and trace it back to original sources.
    """
    )

    with gr.Row():
        input_text = gr.Textbox(
            label="Input Text",
            placeholder="Paste text containing a factual claim...",
            lines=5,
            max_lines=10,
        )
        source_url = gr.Textbox(
            label="Origin URL (optional)",
            placeholder="Paste the URL the text came from to avoid self-citation",
            lines=1,
        )

    submit_btn = gr.Button("Chase the Source", variant="primary")

    with gr.Row():
        with gr.Column():
            claim_output = gr.Markdown(label="Extracted Claim")
        with gr.Column():
            attribution_output = gr.Markdown(label="Attribution")

    sources_output = gr.Markdown(label="Sources")

    submit_btn.click(
        fn=process_input,
        inputs=[input_text, source_url],
        outputs=[claim_output, attribution_output, sources_output],
        show_progress="full",
    )

    gr.Markdown(
        """
    ---
    *This is an MVP for demonstration purposes. Results should be independently verified.*
    """
    )


if __name__ == "__main__":
    app.launch(
        server_name=settings.gradio_server_name, server_port=settings.gradio_server_port
    )
