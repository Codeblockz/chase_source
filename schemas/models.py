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
