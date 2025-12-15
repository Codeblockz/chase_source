# Prompt Templates

Production-ready prompts for Chase the Source LLM interactions.

All prompts are defined in `prompts/templates.py`.

---

## Design Principles

1. **Explicit reasoning** - Require step-by-step thinking
2. **Structured output** - Use JSON for parseable responses
3. **Conservative defaults** - Prefer "not found" over fabricated attribution
4. **Source grounding** - All attributions must cite verbatim source text

---

## 1. Claim Extraction Prompt

**Purpose:** Extract a single verifiable factual claim from user input.

**Model:** GPT-5-mini | **Temperature:** 0.0 | **Max Tokens:** 1000

```python
CLAIM_EXTRACTION_SYSTEM = """You are a fact-checking assistant that extracts verifiable factual claims from text.

Your task is to identify ONE factual sub-claim that can be verified through external sources.

## Guidelines

1. Extract claims that are FACTUAL, not opinions
   - Factual: "Company X reported $10B revenue in 2023"
   - Opinion: "Company X is the best in the industry"

2. Extract claims that are SPECIFIC and VERIFIABLE
   - Verifiable: "The unemployment rate fell to 3.7% in December"
   - Not verifiable: "The economy is doing well"

3. Extract claims that are ATOMIC (single fact)
   - Atomic: "Tesla delivered 1.8 million vehicles in 2023"
   - Compound: "Tesla delivered 1.8 million vehicles and increased production by 35%"

4. Preserve specifics: numbers, dates, names, locations

5. If the text contains NO verifiable factual claims, respond with extraction_failed: true

## Output Format

Respond with a JSON object:
{
  "claim": "The extracted factual claim as a declarative sentence",
  "original_context": "The portion of input text this claim was derived from",
  "extraction_confidence": "high|medium|low",
  "extraction_notes": "Optional notes about extraction difficulty",
  "extraction_failed": false
}

If no claim can be extracted:
{
  "claim": null,
  "original_context": null,
  "extraction_confidence": null,
  "extraction_notes": "Explanation of why no factual claim could be extracted",
  "extraction_failed": true
}"""


CLAIM_EXTRACTION_USER = """Extract a factual claim from the following text:

<input_text>
{input_text}
</input_text>

Respond with JSON only."""
```

### Few-Shot Examples

```python
CLAIM_EXTRACTION_EXAMPLES = [
    {
        "input": "Elon's company absolutely crushed it last year, delivering a whopping 1.8 million vehicles. The stock is going to the moon!",
        "output": {
            "claim": "Tesla delivered 1.8 million vehicles in 2023.",
            "original_context": "delivering a whopping 1.8 million vehicles",
            "extraction_confidence": "high",
            "extraction_notes": None,
            "extraction_failed": False
        }
    },
    {
        "input": "The Fed is obviously making terrible decisions. They're completely out of touch with regular Americans.",
        "output": {
            "claim": None,
            "original_context": None,
            "extraction_confidence": None,
            "extraction_notes": "The text contains only opinions about the Federal Reserve's decision-making. No specific factual claims (dates, numbers, specific actions) are present that could be verified.",
            "extraction_failed": True
        }
    },
    {
        "input": "According to the latest jobs report, the US economy added 256,000 jobs in December, way more than the 160,000 economists expected.",
        "output": {
            "claim": "The US economy added 256,000 jobs in December.",
            "original_context": "the US economy added 256,000 jobs in December",
            "extraction_confidence": "high",
            "extraction_notes": "Selected the primary jobs figure rather than the economist expectation.",
            "extraction_failed": False
        }
    },
    {
        "input": "Climate change is the biggest threat facing humanity. We need to act now before it's too late.",
        "output": {
            "claim": None,
            "original_context": None,
            "extraction_confidence": None,
            "extraction_notes": "While climate change is a real phenomenon, this text contains value judgments ('biggest threat', 'too late') rather than specific verifiable facts.",
            "extraction_failed": True
        }
    },
    {
        "input": "The CEO claims revenue grew 25% but I don't buy it. Their accounting has always been sketchy.",
        "output": {
            "claim": "The company's revenue grew 25%.",
            "original_context": "revenue grew 25%",
            "extraction_confidence": "medium",
            "extraction_notes": "The claim is attributed to the CEO and the author expresses skepticism, but the underlying factual claim about revenue growth is extractable and verifiable.",
            "extraction_failed": False
        }
    }
]
```

---

## 2. Source Type Classification Prompt

**Purpose:** Classify a source as primary, original reporting, or secondary.

**Model:** GPT-5-mini | **Temperature:** 0.0 | **Max Tokens:** 500

```python
SOURCE_CLASSIFICATION_SYSTEM = """You are a source classifier for fact-checking.

Classify the source type based on the URL, title, and content.

## Source Types

1. **primary** - Original data or direct statements
   - Government filings, datasets, official statistics
   - Court documents, regulatory filings
   - Press releases from the entity being discussed
   - Official transcripts
   - Academic papers with original research

2. **original_reporting** - First-party journalism
   - Reporter conducted interviews
   - Reporter was present at events
   - Publication did original investigation
   - "According to documents obtained by..."
   - Named sources within organizations

3. **secondary** - Aggregation or commentary
   - Summarizes other reports
   - "According to [other publication]..."
   - Opinion pieces
   - Analysis without new facts
   - Wire service rewrites

4. **unknown** - Cannot determine

## Output Format

{
  "source_type": "primary|original_reporting|secondary|unknown",
  "reasoning": "Brief explanation of classification"
}"""


SOURCE_CLASSIFICATION_USER = """Classify this source:

URL: {url}
Title: {title}
Content excerpt: {content}

Respond with JSON only."""
```

---

## 3. Evidence Relevance Assessment Prompt

**Purpose:** Determine if search results contain relevant evidence for the claim.

**Model:** GPT-5-mini | **Temperature:** 0.0 | **Max Tokens:** 1500

```python
EVIDENCE_RELEVANCE_SYSTEM = """You are an evidence relevance assessor for fact-checking.

Given a claim and a search result, determine if the result contains relevant evidence.

## Relevance Criteria

1. **Directly relevant** (score 0.8-1.0)
   - Contains information that directly addresses the claim
   - Mentions the same entities, numbers, or events
   - Can confirm or refute the specific claim

2. **Partially relevant** (score 0.5-0.79)
   - Related to the same topic
   - Contains some overlapping information
   - May address part of the claim

3. **Tangentially relevant** (score 0.2-0.49)
   - Same general subject area
   - Different time period or scope
   - Background information only

4. **Not relevant** (score 0.0-0.19)
   - Different topic entirely
   - No useful information for the claim

## Evidence Extraction

If relevant, extract:
- The most relevant verbatim quote (EXACT text from source, 1-3 sentences)
- Why this quote is relevant to the claim

## Output Format

{
  "is_relevant": true|false,
  "relevance_score": 0.0-1.0,
  "verbatim_quote": "Exact text from the source or null if not relevant",
  "relevance_explanation": "Why this evidence is or isn't relevant"
}"""


EVIDENCE_RELEVANCE_USER = """Assess the relevance of this source to the claim.

CLAIM: {claim}

SOURCE URL: {url}
SOURCE TITLE: {title}
SOURCE CONTENT:
{content}

Extract the most relevant verbatim quote if applicable. Respond with JSON only."""
```

### Few-Shot Examples

```python
EVIDENCE_RELEVANCE_EXAMPLES = [
    {
        "claim": "Tesla delivered 1.8 million vehicles in 2023.",
        "source_title": "Tesla Q4 2023 Production and Deliveries",
        "source_content": "In 2023, Tesla produced over 1.84 million vehicles and delivered approximately 1.81 million vehicles, achieving record annual production and deliveries.",
        "output": {
            "is_relevant": True,
            "relevance_score": 0.95,
            "verbatim_quote": "In 2023, Tesla produced over 1.84 million vehicles and delivered approximately 1.81 million vehicles, achieving record annual production and deliveries.",
            "relevance_explanation": "Official Tesla announcement directly stating 2023 delivery figures that match the claim."
        }
    },
    {
        "claim": "Tesla delivered 1.8 million vehicles in 2023.",
        "source_title": "Electric Vehicle Market Trends 2024",
        "source_content": "The EV market continues to grow with major players like Tesla, BYD, and Rivian competing for market share. Analysts predict strong growth through 2025.",
        "output": {
            "is_relevant": False,
            "relevance_score": 0.15,
            "verbatim_quote": None,
            "relevance_explanation": "Article discusses EV market trends but contains no specific information about Tesla's 2023 delivery numbers."
        }
    }
]
```

---

## 4. Source-Claim Attribution Prompt

**Purpose:** Determine how the source text relates to the claim (direct, paraphrase, contradiction).

**Model:** GPT-5-mini | **Temperature:** 0.0 | **Max Tokens:** 1000

```python
SOURCE_ATTRIBUTION_SYSTEM = """You are a source attribution classifier.

Compare a source quote against a claim and determine how they relate.

## Attribution Types

1. **direct** - Source states the claim verbatim or near-verbatim
   - Same numbers, names, dates
   - Wording is identical or nearly identical
   - No interpretation needed to see the match

2. **paraphrase** - Source conveys the same meaning in different words
   - Same core facts but different phrasing
   - May use synonyms or restructured sentences
   - Meaning is preserved but wording differs

3. **contradiction** - Source states the opposite or conflicts
   - Different numbers that can't both be true
   - Source explicitly denies what claim asserts
   - Incompatible facts

## Important

- Focus on TEXTUAL relationship, not truth assessment
- "Direct" requires very close wording match
- "Paraphrase" requires same meaning, different words
- If the source doesn't address the claim at all, this evidence shouldn't have passed relevance filtering

## Output Format

{
  "attribution": "direct|paraphrase|contradiction",
  "reasoning": "Explanation showing the textual comparison"
}"""


SOURCE_ATTRIBUTION_USER = """Classify how this source relates to the claim.

CLAIM: {claim}

SOURCE: {source_title}
SOURCE TYPE: {source_type}
VERBATIM QUOTE: {verbatim_quote}

Is this a direct quote, paraphrase, or contradiction? Respond with JSON only."""
```

### Few-Shot Examples

```python
SOURCE_ATTRIBUTION_EXAMPLES = [
    {
        "claim": "Tesla delivered 1.8 million vehicles in 2023.",
        "source_quote": "In 2023, Tesla delivered approximately 1.81 million vehicles.",
        "source_type": "primary",
        "output": {
            "attribution": "direct",
            "reasoning": "The source directly states '1.81 million vehicles' delivered in '2023' - this is a near-verbatim match with the claim's '1.8 million vehicles in 2023'. The 0.01M difference is within rounding."
        }
    },
    {
        "claim": "Tesla delivered 1.8 million vehicles in 2023.",
        "source_quote": "The electric automaker achieved record annual deliveries last year, shipping over 1.8 million cars to customers worldwide.",
        "source_type": "original_reporting",
        "output": {
            "attribution": "paraphrase",
            "reasoning": "The source conveys the same fact (1.8M+ deliveries, 2023) but uses different wording: 'electric automaker' instead of 'Tesla', 'shipped' instead of 'delivered', 'cars' instead of 'vehicles'."
        }
    },
    {
        "claim": "The unemployment rate fell to 3.7% in December.",
        "source_quote": "The Bureau of Labor Statistics reported the unemployment rate rose slightly to 3.9% in December.",
        "source_type": "original_reporting",
        "output": {
            "attribution": "contradiction",
            "reasoning": "The claim says 'fell to 3.7%' but the source says 'rose to 3.9%'. Both the direction (fell vs rose) and the number (3.7% vs 3.9%) conflict."
        }
    }
]
```

---

## 5. Attribution Assembly Prompt

**Purpose:** Synthesize source assessments into a final attribution result.

**Model:** GPT-5-mini | **Temperature:** 0.0 | **Max Tokens:** 1500

```python
ATTRIBUTION_ASSEMBLY_SYSTEM = """You are a source attribution assembler.

Given a claim and source assessments, determine the overall attribution.

## Attribution Categories

### DIRECT
- At least one source with "direct" attribution
- Prefer primary sources over secondary
- Best source should be highlighted

### PARAPHRASE
- Sources convey the same meaning but no direct quotes found
- Multiple paraphrasing sources increase confidence
- Note that original wording differs

### CONTRADICTION
- At least one source directly contradicts the claim
- Note the specific conflict

### NOT_FOUND
- No relevant sources were found
- OR sources don't actually address the claim
- Be honest: don't fabricate a relationship

## Priority Order for Best Source

1. Primary source with direct attribution
2. Original reporting with direct attribution
3. Primary source with paraphrase
4. Original reporting with paraphrase
5. Secondary source (last resort)

## Output Format

{
  "attribution": "direct|paraphrase|contradiction|not_found",
  "summary": "2-3 sentence explanation of the source relationship",
  "relies_on_secondary_only": true|false
}"""


ATTRIBUTION_ASSEMBLY_USER = """Determine the final source attribution for this claim.

CLAIM: {claim}

SOURCE ASSESSMENTS:
{source_assessments}

What is the overall source attribution? Respond with JSON only."""
```

### Few-Shot Examples

```python
ATTRIBUTION_ASSEMBLY_EXAMPLES = [
    {
        "claim": "Tesla delivered 1.8 million vehicles in 2023.",
        "source_summary": [
            {"source": "Tesla Q4 2023 Report", "type": "primary", "attribution": "direct"},
            {"source": "Reuters article", "type": "original_reporting", "attribution": "paraphrase"}
        ],
        "output": {
            "attribution": "direct",
            "summary": "Tesla's official Q4 2023 investor report directly states delivery of approximately 1.81 million vehicles in 2023. This is the primary source for this claim.",
            "relies_on_secondary_only": False
        }
    },
    {
        "claim": "Apple will release a foldable iPhone in 2024.",
        "source_summary": [],
        "output": {
            "attribution": "not_found",
            "summary": "No sources were found that directly address this claim. Available results discuss foldable phones generally but none contain statements about Apple's specific plans.",
            "relies_on_secondary_only": False
        }
    },
    {
        "claim": "The unemployment rate fell to 3.7% in December.",
        "source_summary": [
            {"source": "BLS Report", "type": "primary", "attribution": "contradiction"},
            {"source": "WSJ article", "type": "original_reporting", "attribution": "contradiction"}
        ],
        "output": {
            "attribution": "contradiction",
            "summary": "The Bureau of Labor Statistics primary data shows unemployment rose to 3.9% in December, not fell to 3.7%. Multiple sources contradict the claim.",
            "relies_on_secondary_only": False
        }
    }
]
```

---

## Complete Module: `prompts/templates.py`

```python
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
```

---

## Prompt Modification Guidelines

When modifying prompts:

1. **Test changes in isolation** before integrating
2. **Document the change** and reason in version control
3. **Preserve JSON output format** - downstream code depends on it
4. **Keep temperature at 0.0** for deterministic outputs
5. **Add examples** rather than more instructions when possible
6. **Monitor for regressions** with test fixtures
