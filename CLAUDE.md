# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Chase the Source** is a source attribution system that extracts factual claims from text, retrieves sources via web search, and classifies how sources relate to the claim: Direct, Paraphrase, Contradiction, or Not Found.

## Technology Stack (Per ADR-001)

- **LangGraph**: Orchestration framework for deterministic node-based workflows
- **OpenAI API**: LLM reasoning for claim extraction, source attribution
- **Tavily**: Web search API for source retrieval
- **Gradio**: Single-page UI

## Architecture

The system uses a 5-node LangGraph workflow:
1. **Claim Extraction** - Extract single factual sub-claim from input text
2. **Source Retrieval** - Query Tavily for candidate sources
3. **Evidence Filtering** - Filter retrieved sources for relevance
4. **Source Comparison** - Classify how each source relates to claim
5. **Attribution Assembly** - Generate final attribution with best source

## Key Design Principles

- All attributions must be traceable to verbatim quoted text
- Prefer "Not Found" over fabricated source relationships
- System must explicitly note when sources are secondary (not original reporting)
- End-to-end execution target: < 30 seconds

## Attribution Categories

- **Direct**: Source states the claim verbatim or near-verbatim
- **Paraphrase**: Source conveys the same meaning in different words
- **Contradiction**: Source states the opposite or conflicts with the claim
- **Not Found**: No sources found that address this specific claim

## Commands

```bash
# Setup
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add API keys

# Run application
python app.py

# Run tests
pytest -m unit                    # Unit tests only
pytest --cov=nodes --cov=schemas  # With coverage
pytest -k "test_claim"            # Pattern match

# Docker
docker compose up                 # Run with Docker
docker build -t chase-the-source . # Build image
```

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/SETUP_GUIDE.md` | Environment setup, Docker, dependencies |
| `docs/DATA_SCHEMAS.md` | Pydantic models and type definitions |
| `docs/PROMPTS.md` | LLM prompt templates with examples |
| `docs/TECHNICAL_SPEC.md` | Node implementations, workflow definition |
| `docs/TESTING_STRATEGY.md` | Test structure, fixtures, mocking patterns |

## Project Structure

```
chase_source/
├── app.py              # Gradio UI entry point
├── graph.py            # LangGraph workflow
├── config.py           # Settings & env loading
├── nodes/              # Pipeline nodes (5 files)
├── schemas/models.py   # Pydantic models
├── prompts/templates.py # LLM prompts
└── tests/              # pytest test suite
```
