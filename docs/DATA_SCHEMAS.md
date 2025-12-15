# Data Schemas

This document defines all Pydantic models and type definitions used in Chase the Source.

All models are defined in `schemas/models.py`.

---

## Overview

```
InputText
    ↓
ExtractedClaim
    ↓
SearchResult[] → Evidence[]
                    ↓
              EvidenceAssessment[]
                    ↓
                 Verdict
```

---

## Core Models

### `InputText`

User-provided text to analyze.

```python
from pydantic import BaseModel, Field, field_validator

class InputText(BaseModel):
    """Validated user input text."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="The text to analyze for factual claims"
    )

    @field_validator("text")
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Normalize whitespace and strip."""
        return " ".join(v.split())
```

**Validation Rules:**
- Minimum 10 characters
- Maximum 5000 characters (~2 paragraphs)
- Whitespace normalized

---

### `ExtractedClaim`

A factual sub-claim extracted from the input text.

```python
from pydantic import BaseModel, Field
from typing import Literal

class ExtractedClaim(BaseModel):
    """A factual claim extracted from user input."""

    claim: str = Field(
        ...,
        description="The extracted factual claim as a single declarative sentence"
    )

    original_context: str = Field(
        ...,
        description="The portion of input text this claim was derived from"
    )

    extraction_confidence: Literal["high", "medium", "low"] = Field(
        ...,
        description="Confidence that this is a verifiable factual claim"
    )

    extraction_notes: str | None = Field(
        default=None,
        description="Notes about extraction difficulty or ambiguity"
    )
```

**Example:**
```python
ExtractedClaim(
    claim="Tesla delivered 1.8 million vehicles in 2023.",
    original_context="Elon's company absolutely crushed it last year, delivering a whopping 1.8 million vehicles.",
    extraction_confidence="high",
    extraction_notes=None
)
```

---

### `SearchResult`

Raw result from Tavily search API.

```python
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

class SearchResult(BaseModel):
    """A single search result from Tavily."""

    url: HttpUrl = Field(
        ...,
        description="URL of the source"
    )

    title: str = Field(
        ...,
        description="Title of the page/article"
    )

    content: str = Field(
        ...,
        description="Extracted text content from the page"
    )

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Tavily relevance score"
    )

    published_date: datetime | None = Field(
        default=None,
        description="Publication date if available"
    )

    raw_content: str | None = Field(
        default=None,
        description="Full raw content if requested"
    )
```

---

### `SourceType`

Enumeration of source categories per PRD.

```python
from enum import Enum

class SourceType(str, Enum):
    """Classification of source reliability."""

    PRIMARY = "primary"
    # Transcripts, filings, datasets, direct statements

    ORIGINAL_REPORTING = "original_reporting"
    # First-party journalism with original investigation

    SECONDARY = "secondary"
    # Aggregation, commentary, or reporting based on other sources

    UNKNOWN = "unknown"
    # Could not determine source type
```

---

### `Evidence`

Filtered and classified evidence item.

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Literal

class Evidence(BaseModel):
    """A piece of evidence relevant to the claim."""

    source_url: HttpUrl = Field(
        ...,
        description="URL of the evidence source"
    )

    source_title: str = Field(
        ...,
        description="Title of the source article/document"
    )

    source_type: SourceType = Field(
        ...,
        description="Classification of the source"
    )

    verbatim_quote: str = Field(
        ...,
        min_length=10,
        description="Exact quoted text from the source"
    )

    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How relevant this evidence is to the claim"
    )

    relevance_explanation: str = Field(
        ...,
        description="Brief explanation of why this evidence is relevant"
    )
```

**Example:**
```python
Evidence(
    source_url="https://ir.tesla.com/press-release/tesla-q4-2023-update",
    source_title="Tesla Q4 2023 Update",
    source_type=SourceType.PRIMARY,
    verbatim_quote="In 2023, we produced 1.85 million vehicles and delivered over 1.8 million vehicles.",
    relevance_score=0.95,
    relevance_explanation="Official Tesla investor relations document directly stating 2023 delivery numbers."
)
```

---

### `EvidenceAssessment`

How a single piece of evidence relates to the claim.

```python
from pydantic import BaseModel, Field
from typing import Literal

class EvidenceAssessment(BaseModel):
    """Assessment of how evidence relates to the claim."""

    evidence: Evidence = Field(
        ...,
        description="The evidence being assessed"
    )

    attribution: Literal["direct", "paraphrase", "contradiction"] = Field(
        ...,
        description="How this source relates to the claim"
    )

    reasoning: str = Field(
        ...,
        description="Explanation of why this is a direct quote, paraphrase, or contradiction"
    )
```

**Attribution Types:**
- `direct` - Source states the claim verbatim or near-verbatim
- `paraphrase` - Source conveys the same meaning in different words
- `contradiction` - Source states the opposite or conflicts with the claim

---

### `AttributionType`

The four possible source attribution outcomes per PRD.

```python
from enum import Enum

class AttributionType(str, Enum):
    """Possible source attribution outcomes."""

    DIRECT = "direct"
    # Source states the claim verbatim or near-verbatim

    PARAPHRASE = "paraphrase"
    # Source conveys the same meaning in different words

    CONTRADICTION = "contradiction"
    # Source states the opposite or conflicts with the claim

    NOT_FOUND = "not_found"
    # No sources found that address this specific claim
```

---

### `SourceAttribution`

Final output of the source attribution pipeline.

```python
from pydantic import BaseModel, Field

class SourceAttribution(BaseModel):
    """Final source attribution result."""

    claim: str = Field(
        ...,
        description="The claim that was traced"
    )

    attribution: AttributionType = Field(
        ...,
        description="How sources relate to the claim"
    )

    summary: str = Field(
        ...,
        max_length=500,
        description="Human-readable explanation of the attribution"
    )

    evidence_list: list[EvidenceAssessment] = Field(
        ...,
        min_length=0,
        max_length=5,
        description="Sources found and how they relate to the claim"
    )

    best_source: EvidenceAssessment | None = Field(
        default=None,
        description="The strongest source (primary > original reporting > secondary)"
    )

    relies_on_secondary_only: bool = Field(
        ...,
        description="True if only secondary sources were found"
    )
```

**Example:**
```python
SourceAttribution(
    claim="Tesla delivered 1.8 million vehicles in 2023.",
    attribution=AttributionType.DIRECT,
    summary="Tesla's official Q4 2023 report directly states delivery of 1.81 million vehicles.",
    evidence_list=[...],
    best_source=evidence_list[0],
    relies_on_secondary_only=False
)
```

---

## LangGraph State

### `GraphState`

The state object passed between LangGraph nodes.

```python
from pydantic import BaseModel, Field
from typing import TypedDict
from langgraph.graph import MessagesState

class GraphState(TypedDict):
    """State passed between LangGraph nodes."""

    # Input
    input_text: str

    # After claim extraction
    extracted_claim: ExtractedClaim | None
    extraction_failed: bool
    extraction_error: str | None

    # After search
    search_results: list[SearchResult]
    search_query: str | None

    # After evidence filtering
    evidence: list[Evidence]

    # After evidence comparison
    assessments: list[EvidenceAssessment]

    # Final output
    result: SourceAttribution | None

    # Error tracking
    errors: list[str]
```

**State Transitions:**

| Node | Reads | Writes |
|------|-------|--------|
| ClaimExtractor | `input_text` | `extracted_claim`, `extraction_failed`, `extraction_error` |
| SourceRetriever | `extracted_claim` | `search_results`, `search_query` |
| EvidenceFilter | `search_results`, `extracted_claim` | `evidence` |
| SourceComparer | `evidence`, `extracted_claim` | `assessments` |
| AttributionAssembler | `assessments`, `extracted_claim` | `result` |

---

## Validation Helpers

### Claim Validation

```python
def is_verifiable_claim(claim: str) -> bool:
    """Check if a claim is potentially verifiable."""
    # Must be a declarative statement
    if claim.endswith("?"):
        return False

    # Must contain some specificity (numbers, names, dates)
    import re
    has_specifics = bool(
        re.search(r'\d+', claim) or  # numbers
        re.search(r'[A-Z][a-z]+', claim)  # proper nouns
    )

    return has_specifics
```

### URL Validation

```python
from pydantic import HttpUrl, ValidationError

def validate_source_url(url: str) -> HttpUrl | None:
    """Validate and normalize a URL."""
    try:
        return HttpUrl(url)
    except ValidationError:
        return None
```

---

## Complete Module: `schemas/models.py`

```python
"""
Data models for Chase the Source.

All Pydantic models used throughout the application.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, TypedDict

from pydantic import BaseModel, Field, HttpUrl, field_validator


# === Enums ===

class SourceType(str, Enum):
    PRIMARY = "primary"
    ORIGINAL_REPORTING = "original_reporting"
    SECONDARY = "secondary"
    UNKNOWN = "unknown"


class AttributionType(str, Enum):
    DIRECT = "direct"
    PARAPHRASE = "paraphrase"
    CONTRADICTION = "contradiction"
    NOT_FOUND = "not_found"


# === Input Models ===

class InputText(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)

    @field_validator("text")
    @classmethod
    def clean_text(cls, v: str) -> str:
        return " ".join(v.split())


# === Extraction Models ===

class ExtractedClaim(BaseModel):
    claim: str
    original_context: str
    extraction_confidence: Literal["high", "medium", "low"]
    extraction_notes: str | None = None


# === Search Models ===

class SearchResult(BaseModel):
    url: HttpUrl
    title: str
    content: str
    score: float = Field(ge=0.0, le=1.0)
    published_date: datetime | None = None
    raw_content: str | None = None


# === Evidence Models ===

class Evidence(BaseModel):
    source_url: HttpUrl
    source_title: str
    source_type: SourceType
    verbatim_quote: str = Field(min_length=10)
    relevance_score: float = Field(ge=0.0, le=1.0)
    relevance_explanation: str


class EvidenceAssessment(BaseModel):
    evidence: Evidence
    attribution: Literal["direct", "paraphrase", "contradiction"]
    reasoning: str


# === Output Models ===

class SourceAttribution(BaseModel):
    claim: str
    attribution: AttributionType
    summary: str = Field(max_length=500)
    evidence_list: list[EvidenceAssessment] = Field(min_length=0, max_length=5)
    best_source: EvidenceAssessment | None = None
    relies_on_secondary_only: bool


# === LangGraph State ===

class GraphState(TypedDict):
    input_text: str
    extracted_claim: ExtractedClaim | None
    extraction_failed: bool
    extraction_error: str | None
    search_results: list[SearchResult]
    search_query: str | None
    evidence: list[Evidence]
    assessments: list[EvidenceAssessment]
    result: SourceAttribution | None
    errors: list[str]
```
