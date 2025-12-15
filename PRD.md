# Chase the Source — Product Requirements Document (PRD)

## 1. Problem Statement

Articles and social posts often contain **interpretive or opinionated language** that embeds **implicit factual sub-claims**. Readers cannot easily trace these claims back to **original reporting or primary sources**, nor determine whether the source material **directly states**, **paraphrases**, or **contradicts** the claim.

---

## 2. Goal

Given a short input text, the system will:

1. **Extract one factual sub-claim** (even if embedded in opinionated language)
2. Retrieve relevant sources via web search
3. Classify the source-to-claim relationship: **Direct, Paraphrase, Contradiction, or Not Found**
4. Present **verbatim evidence** showing where the claim originated

This is an **ephemeral, single-session MVP** focused on source attribution and transparency.

---

## 3. Non-Goals

* No persistent storage or user accounts
* No batch or multi-claim processing
* No automated truth scoring
* No political stance labeling
* No browser extension or API productization

---

## 4. Target User

* Journalists / researchers (prototype-level)
* Technical evaluators (hiring managers)
* Advanced users interested in source attribution

---

## 5. Core User Flow

1. User pastes a paragraph (article excerpt, post, commentary)
2. System extracts **one factual sub-claim**
3. System retrieves sources using Tavily
4. System evaluates evidence using grounded LLM reasoning
5. System displays:

   * Extracted claim
   * Verdict
   * Sources and quoted evidence

---

## 6. Functional Requirements

### 6.1 Input

* Free-form text (≤ 2 paragraphs)

### 6.2 Claim Extraction

* System **attempts** to extract a factual sub-claim even if the input is opinionated
* If no factual claim can be reasonably isolated, the system must state this explicitly

### 6.3 Source Retrieval

* Original reporting **is allowed**
* Sources may be:

  * Primary (transcripts, filings, datasets, direct statements)
  * Original reporting (first-party journalism)
  * Secondary reporting (clearly labeled)

### 6.4 Source Attribution Categories

* **Direct** – Source states the claim verbatim or near-verbatim
* **Paraphrase** – Source conveys the same meaning in different words
* **Contradiction** – Source states the opposite or conflicts with the claim
* **Not Found** – No sources found that address this specific claim

---

## 7. Output Requirements

### 7.1 Required Outputs

* **Extracted Claim** (single sentence)
* **Attribution**: Direct | Paraphrase | Contradiction | Not Found
* **Evidence List** (1–5 items):

  * Source URL
  * Source type (primary / original reporting / secondary)
  * Verbatim quoted excerpt
  * How the source relates to the claim (direct quote, paraphrase, or contradiction)

### 7.2 Transparency

* All attributions must be traceable to verbatim quoted text
* System must explicitly note when sources are secondary (not original reporting)
* System must show the "chain" from claim → source quote

---

## 8. UI Requirements (Gradio)

* Single-page interface
* Text input field
* "Chase the Source" action button
* Structured output sections:

  * Extracted Claim
  * Verdict
  * Sources & Evidence

No advanced settings or debug UI in MVP.

---

## 9. Success Criteria (MVP)

* End-to-end execution < 30 seconds
* Claim extraction is understandable and defensible
* Attribution category matches the quoted evidence
* System returns **Not Found** rather than fabricating a source relationship

---

## 10. Known Limitations

* Temporal mismatches (old vs recent reporting)
* Search result noise
* Ambiguous or compound claims
* No human-in-the-loop correction

---
