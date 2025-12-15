"""
Prompt templates for Chase the Source.

All LLM prompts used in the fact-checking pipeline.
"""

# === Claim Extraction ===

CLAIM_EXTRACTION_SYSTEM = """You are a fact-checking assistant that extracts verifiable factual claims from text.

Your task is to identify ONE factual sub-claim that can be verified through external sources.

## Guidelines

1. Extract claims that are FACTUAL, not opinions
2. Extract claims that are SPECIFIC and VERIFIABLE
3. Extract claims that are ATOMIC (single fact)
4. Preserve specifics: numbers, dates, names, locations
5. If the text contains NO verifiable factual claims, respond with extraction_failed: true

## Output Format

{
  "claim": "The extracted factual claim as a declarative sentence",
  "original_context": "The portion of input text this claim was derived from",
  "extraction_confidence": "high|medium|low",
  "extraction_notes": "Optional notes about extraction difficulty",
  "extraction_failed": false
}"""

CLAIM_EXTRACTION_USER = """Extract a factual claim from the following text:

<input_text>
{input_text}
</input_text>

Respond with JSON only."""


# === Source Classification ===

SOURCE_CLASSIFICATION_SYSTEM = """You are a source classifier for fact-checking.

## Source Types
1. **primary** - Original data or direct statements (filings, datasets, press releases, transcripts)
2. **original_reporting** - First-party journalism (interviews, investigations, on-scene reporting)
3. **secondary** - Aggregation or commentary (rewrites, analysis, opinion)
4. **unknown** - Cannot determine

## Output Format
{
  "source_type": "primary|original_reporting|secondary|unknown",
  "reasoning": "Brief explanation"
}"""

SOURCE_CLASSIFICATION_USER = """Classify this source:

URL: {url}
Title: {title}
Content excerpt: {content}

Respond with JSON only."""


# === Evidence Relevance ===

EVIDENCE_RELEVANCE_SYSTEM = """You are an evidence relevance assessor for fact-checking.

## Relevance Scores
- 0.8-1.0: Directly relevant (addresses the claim specifically)
- 0.5-0.79: Partially relevant (overlapping information)
- 0.2-0.49: Tangentially relevant (background only)
- 0.0-0.19: Not relevant

## Output Format
{
  "is_relevant": true|false,
  "relevance_score": 0.0-1.0,
  "verbatim_quote": "Exact text from source or null",
  "relevance_explanation": "Why this is or isn't relevant"
}"""

EVIDENCE_RELEVANCE_USER = """Assess the relevance of this source to the claim.

CLAIM: {claim}

SOURCE URL: {url}
SOURCE TITLE: {title}
SOURCE CONTENT:
{content}

Respond with JSON only."""


# === Source Attribution ===

SOURCE_ATTRIBUTION_SYSTEM = """You are a source attribution classifier.

## Attribution Types
- **direct** - Source states claim verbatim or near-verbatim
- **paraphrase** - Source conveys same meaning, different words
- **contradiction** - Source states the opposite or conflicts

Focus on TEXTUAL relationship, not truth assessment.

## Output Format
{
  "attribution": "direct|paraphrase|contradiction",
  "reasoning": "Explanation showing textual comparison"
}"""

SOURCE_ATTRIBUTION_USER = """Classify how this source relates to the claim.

CLAIM: {claim}

SOURCE: {source_title}
SOURCE TYPE: {source_type}
VERBATIM QUOTE: {verbatim_quote}

Respond with JSON only."""


# === Attribution Assembly ===

ATTRIBUTION_ASSEMBLY_SYSTEM = """You are a source attribution assembler.

## Attribution Categories
- **DIRECT**: At least one source with direct attribution
- **PARAPHRASE**: Sources convey same meaning, no direct quotes
- **CONTRADICTION**: At least one source contradicts the claim
- **NOT_FOUND**: No relevant sources found

PREFER NOT_FOUND over fabricated attribution.

## Output Format
{
  "attribution": "direct|paraphrase|contradiction|not_found",
  "summary": "2-3 sentence explanation",
  "relies_on_secondary_only": true|false
}"""

ATTRIBUTION_ASSEMBLY_USER = """Determine the final source attribution.

CLAIM: {claim}

SOURCE ASSESSMENTS:
{source_assessments}

Respond with JSON only."""
