# Technical Specification

Implementation guide for Chase the Source fact-checking system.

---

## Project Structure

```
chase_source/
├── app.py                 # Gradio UI entry point
├── graph.py               # LangGraph workflow definition
├── config.py              # Settings & environment loading
├── nodes/
│   ├── __init__.py
│   ├── claim_extractor.py
│   ├── source_retriever.py
│   ├── evidence_filter.py
│   ├── source_comparer.py
│   └── attribution_assembler.py
├── schemas/
│   ├── __init__.py
│   └── models.py          # Pydantic models (see DATA_SCHEMAS.md)
├── prompts/
│   └── templates.py       # Prompt strings (see PROMPTS.md)
├── tests/                 # Test suite (see TESTING_STRATEGY.md)
├── docs/                  # This documentation
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              GRADIO UI                                   │
│                            (app.py)                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           LANGGRAPH WORKFLOW                             │
│                             (graph.py)                                   │
│                                                                          │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│   │  Claim   │───▶│  Source  │───▶│ Evidence │───▶│  Source  │          │
│   │Extractor │    │Retriever │    │  Filter  │    │ Comparer │          │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│        │                                               │                 │
│        │ (extraction_failed?)                          ▼                 │
│        │                                        ┌───────────┐            │
│        └───────────────────────────────────────▶│Attribution│            │
│                                                 │ Assembler │            │
│                                                 └───────────┘            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
               ┌──────────────┐         ┌──────────────┐
               │  OpenAI API  │         │  Tavily API  │
               │  (GPT-5-mini)│         │  (Search)    │
               └──────────────┘         └──────────────┘
```

---

## LangGraph Workflow Definition

### File: `graph.py`

```python
"""
LangGraph workflow for Chase the Source.
"""

from langgraph.graph import StateGraph, END
from schemas.models import GraphState
from nodes.claim_extractor import extract_claim
from nodes.source_retriever import retrieve_sources
from nodes.evidence_filter import filter_evidence
from nodes.source_comparer import compare_sources
from nodes.attribution_assembler import assemble_attribution


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
            "attribution_assembler": "attribution_assembler"
        }
    )
    workflow.add_edge("source_retriever", "evidence_filter")
    workflow.add_edge("evidence_filter", "source_comparer")
    workflow.add_edge("source_comparer", "attribution_assembler")
    workflow.add_edge("attribution_assembler", END)

    # Compile
    return workflow.compile()


# Singleton graph instance
graph = build_graph()


def run_source_check(input_text: str) -> GraphState:
    """Execute the source attribution pipeline."""
    initial_state: GraphState = {
        "input_text": input_text,
        "extracted_claim": None,
        "extraction_failed": False,
        "extraction_error": None,
        "search_results": [],
        "search_query": None,
        "evidence": [],
        "assessments": [],
        "result": None,
        "errors": []
    }

    result = graph.invoke(initial_state)
    return result
```

---

## Node Implementations

### Node 1: Claim Extractor

**File:** `nodes/claim_extractor.py`

**Purpose:** Extract a single verifiable factual claim from user input.

**Input State:**
- `input_text: str`

**Output State:**
- `extracted_claim: ExtractedClaim | None`
- `extraction_failed: bool`
- `extraction_error: str | None`

```python
"""
Claim extraction node.
"""

import json
import logging
from openai import OpenAI
from schemas.models import GraphState, ExtractedClaim
from prompts.templates import CLAIM_EXTRACTION_SYSTEM, CLAIM_EXTRACTION_USER
from config import settings

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def extract_claim(state: GraphState) -> GraphState:
    """
    Extract a factual claim from input text.

    Args:
        state: Current graph state with input_text

    Returns:
        Updated state with extracted_claim or extraction_failed
    """
    input_text = state["input_text"]
    logger.info(f"Extracting claim from {len(input_text)} chars")

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": CLAIM_EXTRACTION_SYSTEM},
                {"role": "user", "content": CLAIM_EXTRACTION_USER.format(
                    input_text=input_text
                )}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        if result.get("extraction_failed", False):
            logger.warning(f"Extraction failed: {result.get('extraction_notes')}")
            return {
                **state,
                "extracted_claim": None,
                "extraction_failed": True,
                "extraction_error": result.get("extraction_notes")
            }

        claim = ExtractedClaim(
            claim=result["claim"],
            original_context=result["original_context"],
            extraction_confidence=result["extraction_confidence"],
            extraction_notes=result.get("extraction_notes")
        )

        logger.info(f"Extracted claim: {claim.claim}")
        return {
            **state,
            "extracted_claim": claim,
            "extraction_failed": False,
            "extraction_error": None
        }

    except Exception as e:
        logger.error(f"Claim extraction error: {e}")
        return {
            **state,
            "extracted_claim": None,
            "extraction_failed": True,
            "extraction_error": str(e),
            "errors": state.get("errors", []) + [f"Claim extraction: {e}"]
        }
```

**Edge Cases:**
- Empty input → extraction_failed with appropriate message
- Opinion-only text → extraction_failed with explanation
- Multiple claims → extracts first/strongest claim
- API timeout → extraction_failed with error

---

### Node 2: Source Retriever

**File:** `nodes/source_retriever.py`

**Purpose:** Query Tavily to find sources related to the claim.

**Input State:**
- `extracted_claim: ExtractedClaim`

**Output State:**
- `search_results: list[SearchResult]`
- `search_query: str`

```python
"""
Source retrieval node using Tavily.
"""

import logging
from tavily import TavilyClient
from schemas.models import GraphState, SearchResult
from config import settings

logger = logging.getLogger(__name__)
tavily = TavilyClient(api_key=settings.tavily_api_key)


def retrieve_sources(state: GraphState) -> GraphState:
    """
    Retrieve sources from Tavily for the extracted claim.

    Args:
        state: Current graph state with extracted_claim

    Returns:
        Updated state with search_results
    """
    claim = state["extracted_claim"]
    if not claim:
        logger.warning("No claim to search for")
        return {**state, "search_results": [], "search_query": None}

    # Build search query from claim
    search_query = claim.claim
    logger.info(f"Searching Tavily: {search_query}")

    try:
        response = tavily.search(
            query=search_query,
            search_depth=settings.tavily_search_depth,
            max_results=settings.tavily_max_results,
            include_raw_content=True
        )

        results = []
        for item in response.get("results", []):
            try:
                result = SearchResult(
                    url=item["url"],
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    published_date=item.get("published_date"),
                    raw_content=item.get("raw_content")
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"Skipping malformed result: {e}")
                continue

        logger.info(f"Retrieved {len(results)} search results")
        return {
            **state,
            "search_results": results,
            "search_query": search_query
        }

    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return {
            **state,
            "search_results": [],
            "search_query": search_query,
            "errors": state.get("errors", []) + [f"Source retrieval: {e}"]
        }
```

**Tavily Configuration:**
- `search_depth`: "advanced" for better results
- `max_results`: 10 (filter down later)
- `include_raw_content`: True for full text extraction

---

### Node 3: Evidence Filter

**File:** `nodes/evidence_filter.py`

**Purpose:** Filter search results for relevance and extract evidence.

**Input State:**
- `search_results: list[SearchResult]`
- `extracted_claim: ExtractedClaim`

**Output State:**
- `evidence: list[Evidence]`

```python
"""
Evidence filtering node.
"""

import json
import logging
from openai import OpenAI
from schemas.models import GraphState, Evidence, SourceType, SearchResult
from prompts.templates import (
    EVIDENCE_RELEVANCE_SYSTEM,
    EVIDENCE_RELEVANCE_USER,
    SOURCE_CLASSIFICATION_SYSTEM,
    SOURCE_CLASSIFICATION_USER
)
from config import settings

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def classify_source(url: str, title: str, content: str) -> SourceType:
    """Classify source type using LLM."""
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=500,
            messages=[
                {"role": "system", "content": SOURCE_CLASSIFICATION_SYSTEM},
                {"role": "user", "content": SOURCE_CLASSIFICATION_USER.format(
                    url=url,
                    title=title,
                    content=content[:1000]  # Truncate for classification
                )}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return SourceType(result.get("source_type", "unknown"))
    except Exception as e:
        logger.warning(f"Source classification failed: {e}")
        return SourceType.UNKNOWN


def assess_relevance(claim: str, result: SearchResult) -> dict | None:
    """Assess relevance and extract evidence from a search result."""
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": EVIDENCE_RELEVANCE_SYSTEM},
                {"role": "user", "content": EVIDENCE_RELEVANCE_USER.format(
                    claim=claim,
                    url=str(result.url),
                    title=result.title,
                    content=result.content[:3000]  # Truncate for context window
                )}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.warning(f"Relevance assessment failed: {e}")
        return None


def filter_evidence(state: GraphState) -> GraphState:
    """
    Filter search results for relevant evidence.

    Args:
        state: Current graph state with search_results and extracted_claim

    Returns:
        Updated state with filtered evidence list
    """
    claim = state.get("extracted_claim")
    results = state.get("search_results", [])

    if not claim or not results:
        logger.warning("No claim or search results to filter")
        return {**state, "evidence": []}

    claim_text = claim.claim
    evidence_list = []

    for result in results:
        # Assess relevance
        assessment = assess_relevance(claim_text, result)
        if not assessment:
            continue

        if not assessment.get("is_relevant", False):
            logger.debug(f"Filtered out: {result.title} (not relevant)")
            continue

        if assessment.get("relevance_score", 0) < 0.5:
            logger.debug(f"Filtered out: {result.title} (low score)")
            continue

        # Classify source type
        source_type = classify_source(
            str(result.url),
            result.title,
            result.content
        )

        # Build evidence object
        try:
            evidence = Evidence(
                source_url=result.url,
                source_title=result.title,
                source_type=source_type,
                verbatim_quote=assessment["verbatim_quote"],
                relevance_score=assessment["relevance_score"],
                relevance_explanation=assessment["relevance_explanation"]
            )
            evidence_list.append(evidence)
            logger.info(f"Found evidence: {result.title} ({source_type.value})")
        except Exception as e:
            logger.warning(f"Failed to create evidence object: {e}")
            continue

        # Limit to top 5 evidence items
        if len(evidence_list) >= 5:
            break

    # Sort by relevance score
    evidence_list.sort(key=lambda e: e.relevance_score, reverse=True)

    logger.info(f"Filtered to {len(evidence_list)} evidence items")
    return {**state, "evidence": evidence_list}
```

**Filtering Logic:**
1. Skip results with relevance score < 0.5
2. Extract verbatim quotes from relevant results
3. Classify source type (primary/original/secondary)
4. Limit to top 5 evidence items
5. Sort by relevance score

---

### Node 4: Source Comparer

**File:** `nodes/source_comparer.py`

**Purpose:** Classify how each source relates to the claim (direct, paraphrase, contradiction).

**Input State:**
- `evidence: list[Evidence]`
- `extracted_claim: ExtractedClaim`

**Output State:**
- `assessments: list[EvidenceAssessment]`

```python
"""
Source comparison node.
"""

import json
import logging
from openai import OpenAI
from schemas.models import GraphState, Evidence, EvidenceAssessment
from prompts.templates import SOURCE_ATTRIBUTION_SYSTEM, SOURCE_ATTRIBUTION_USER
from config import settings

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def classify_source_attribution(claim: str, evidence: Evidence) -> EvidenceAssessment | None:
    """Classify how a single source relates to the claim."""
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SOURCE_ATTRIBUTION_SYSTEM},
                {"role": "user", "content": SOURCE_ATTRIBUTION_USER.format(
                    claim=claim,
                    source_title=evidence.source_title,
                    source_type=evidence.source_type.value,
                    verbatim_quote=evidence.verbatim_quote
                )}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        return EvidenceAssessment(
            evidence=evidence,
            attribution=result["attribution"],
            reasoning=result["reasoning"]
        )

    except Exception as e:
        logger.warning(f"Source attribution failed: {e}")
        return None


def compare_sources(state: GraphState) -> GraphState:
    """
    Classify how all sources relate to the claim.

    Args:
        state: Current graph state with evidence and extracted_claim

    Returns:
        Updated state with assessments
    """
    claim = state.get("extracted_claim")
    evidence_list = state.get("evidence", [])

    if not claim or not evidence_list:
        logger.warning("No claim or evidence to compare")
        return {**state, "assessments": []}

    claim_text = claim.claim
    assessments = []

    for evidence in evidence_list:
        assessment = classify_source_attribution(claim_text, evidence)
        if assessment:
            assessments.append(assessment)
            logger.info(
                f"Attribution: {evidence.source_title} -> {assessment.attribution}"
            )

    logger.info(f"Completed {len(assessments)} source attributions")
    return {**state, "assessments": assessments}
```

---

### Node 5: Attribution Assembler

**File:** `nodes/attribution_assembler.py`

**Purpose:** Synthesize source assessments into final attribution result.

**Input State:**
- `assessments: list[EvidenceAssessment]`
- `extracted_claim: ExtractedClaim`
- `extraction_failed: bool`
- `extraction_error: str | None`

**Output State:**
- `result: SourceAttribution`

```python
"""
Attribution assembly node.
"""

import json
import logging
from openai import OpenAI
from schemas.models import (
    GraphState, SourceAttribution, AttributionType, EvidenceAssessment, SourceType
)
from prompts.templates import ATTRIBUTION_ASSEMBLY_SYSTEM, ATTRIBUTION_ASSEMBLY_USER
from config import settings

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def format_assessments_for_prompt(assessments: list[EvidenceAssessment]) -> str:
    """Format source assessments for the attribution prompt."""
    if not assessments:
        return "No relevant sources found."

    lines = []
    for i, a in enumerate(assessments, 1):
        lines.append(f"""
Source {i}:
- Title: {a.evidence.source_title}
- Type: {a.evidence.source_type.value}
- Quote: "{a.evidence.verbatim_quote}"
- Attribution: {a.attribution}
- Reasoning: {a.reasoning}
""")
    return "\n".join(lines)


def find_best_source(assessments: list[EvidenceAssessment]) -> EvidenceAssessment | None:
    """Find the best source based on type and attribution."""
    if not assessments:
        return None

    # Priority: primary > original_reporting > secondary
    # Within each, prefer direct > paraphrase
    def score(a: EvidenceAssessment) -> tuple:
        type_score = {
            SourceType.PRIMARY: 3,
            SourceType.ORIGINAL_REPORTING: 2,
            SourceType.SECONDARY: 1,
            SourceType.UNKNOWN: 0
        }.get(a.evidence.source_type, 0)

        attr_score = {
            "direct": 2,
            "paraphrase": 1,
            "contradiction": 0
        }.get(a.attribution, 0)

        return (type_score, attr_score)

    return max(assessments, key=score)


def assemble_attribution(state: GraphState) -> GraphState:
    """
    Assemble final attribution from source assessments.

    Args:
        state: Current graph state with assessments and extracted_claim

    Returns:
        Updated state with final result
    """
    # Handle extraction failure case
    if state.get("extraction_failed", False):
        result = SourceAttribution(
            claim="[No factual claim could be extracted]",
            attribution=AttributionType.NOT_FOUND,
            summary=state.get("extraction_error") or "Could not extract a verifiable factual claim from the input.",
            evidence_list=[],
            best_source=None,
            relies_on_secondary_only=False
        )
        return {**state, "result": result}

    claim = state.get("extracted_claim")
    assessments = state.get("assessments", [])

    # Handle no sources found
    if not assessments:
        result = SourceAttribution(
            claim=claim.claim if claim else "[Unknown]",
            attribution=AttributionType.NOT_FOUND,
            summary="No relevant sources were found that address this claim.",
            evidence_list=[],
            best_source=None,
            relies_on_secondary_only=False
        )
        return {**state, "result": result}

    # Check if all evidence is secondary
    relies_on_secondary = all(
        a.evidence.source_type == SourceType.SECONDARY
        for a in assessments
    )

    # Find best source
    best_source = find_best_source(assessments)

    # Format assessments for prompt
    assessments_text = format_assessments_for_prompt(assessments)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.0,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": ATTRIBUTION_ASSEMBLY_SYSTEM},
                {"role": "user", "content": ATTRIBUTION_ASSEMBLY_USER.format(
                    claim=claim.claim,
                    source_assessments=assessments_text
                )}
            ],
            response_format={"type": "json_object"}
        )

        llm_result = json.loads(response.choices[0].message.content)

        result = SourceAttribution(
            claim=claim.claim,
            attribution=AttributionType(llm_result["attribution"]),
            summary=llm_result["summary"],
            evidence_list=assessments,
            best_source=best_source,
            relies_on_secondary_only=relies_on_secondary or llm_result.get("relies_on_secondary_only", False)
        )

        logger.info(f"Final attribution: {result.attribution.value}")
        return {**state, "result": result}

    except Exception as e:
        logger.error(f"Attribution assembly error: {e}")
        result = SourceAttribution(
            claim=claim.claim,
            attribution=AttributionType.NOT_FOUND,
            summary=f"An error occurred while assembling the attribution: {e}",
            evidence_list=assessments,
            best_source=best_source,
            relies_on_secondary_only=relies_on_secondary
        )
        return {
            **state,
            "result": result,
            "errors": state.get("errors", []) + [f"Attribution assembly: {e}"]
        }
```

---

## Configuration

### File: `config.py`

```python
"""
Application configuration.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # API Keys
    openai_api_key: str
    tavily_api_key: str

    # OpenAI Configuration
    openai_model: str = "gpt-5-mini"
    openai_temperature: float = 0.0
    openai_max_tokens: int = 2000

    # Tavily Configuration
    tavily_max_results: int = 10
    tavily_search_depth: str = "advanced"

    # Application Settings
    log_level: str = "INFO"
    gradio_server_port: int = 7860
    gradio_server_name: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
```

---

## Gradio UI

### File: `app.py`

```python
"""
Gradio UI for Chase the Source.
"""

import logging
import gradio as gr
from graph import run_source_check
from schemas.models import SourceAttribution, AttributionType, SourceType
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
        AttributionType.NOT_FOUND: "⚪"
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
                SourceType.UNKNOWN: "❓ Unknown"
            }.get(e.source_type, "Unknown")

            attribution_emoji = {
                "direct": "🎯",
                "paraphrase": "📝",
                "contradiction": "❌"
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


def process_input(text: str) -> tuple[str, str, str]:
    """
    Process user input through the source attribution pipeline.

    Args:
        text: User-provided text to analyze

    Returns:
        Tuple of (claim, attribution, sources) formatted strings
    """
    if not text or len(text.strip()) < 10:
        return (
            "**Error:** Please provide at least 10 characters of text.",
            "",
            ""
        )

    logger.info(f"Processing input: {len(text)} characters")

    try:
        result = run_source_check(text)
        attribution = result.get("result")

        if not attribution:
            return (
                "**Error:** Failed to produce a result.",
                "",
                ""
            )

        return format_attribution_output(attribution)

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return (
            f"**Error:** An error occurred during processing: {e}",
            "",
            ""
        )


# Build Gradio interface
with gr.Blocks(title="Chase the Source", theme=gr.themes.Soft()) as app:
    gr.Markdown("""
    # 🔍 Chase the Source

    Paste an article excerpt, social post, or commentary below.
    The system will extract a factual claim and trace it back to original sources.
    """)

    with gr.Row():
        input_text = gr.Textbox(
            label="Input Text",
            placeholder="Paste text containing a factual claim...",
            lines=5,
            max_lines=10
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
        inputs=[input_text],
        outputs=[claim_output, attribution_output, sources_output]
    )

    gr.Markdown("""
    ---
    *This is an MVP for demonstration purposes. Results should be independently verified.*
    """)


if __name__ == "__main__":
    app.launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port
    )
```

---

## Error Handling Strategy

### Error Categories

| Category | Handling | User Message |
|----------|----------|--------------|
| API Rate Limit | Retry with backoff | "Service temporarily busy, please try again" |
| Invalid API Key | Fail fast | "Configuration error - check API keys" |
| Network Error | Retry once | "Network error - please try again" |
| LLM Parse Error | Return NOT_FOUND | "Could not process response" |
| No Results Found | Return NOT_FOUND | "No relevant sources found" |

### Logging Strategy

```python
# Log levels by component
LOGGING = {
    "app": "INFO",           # User-facing operations
    "graph": "INFO",         # Workflow execution
    "nodes.*": "DEBUG",      # Node internals (verbose)
    "openai": "WARNING",     # API client
    "httpx": "WARNING"       # HTTP client
}
```

---

## Performance Considerations

### Target: < 30 seconds end-to-end

| Node | Expected Time | Notes |
|------|---------------|-------|
| Claim Extraction | 1-2s | Single LLM call |
| Source Retrieval | 2-4s | Tavily API |
| Evidence Filter | 5-10s | Multiple LLM calls (parallel possible) |
| Source Comparer | 3-6s | Multiple LLM calls (parallel possible) |
| Attribution Assembly | 1-2s | Single LLM call |
| **Total** | **12-24s** | Within target |

### Optimization Opportunities (Post-MVP)

1. Parallelize evidence filtering LLM calls
2. Parallelize evidence comparison LLM calls
3. Cache Tavily results for identical queries
4. Use streaming for perceived performance
