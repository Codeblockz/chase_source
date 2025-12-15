# Architecture Decision Record (ADR)



## ADR-001: MVP Architecture & Tooling



### Status



Accepted (MVP)



---



## Context



The system requires:



* Explicit reasoning steps

* Conditional refusal or uncertainty

* Evidence-grounded outputs

* Fast prototyping with minimal frontend work



---



## Decisions



### 1. LangGraph for Orchestration



LangGraph will define a **deterministic, node-based workflow**.



**Proposed Nodes**



1. Claim Extraction

2. Search & Retrieval (Tavily)

3. Evidence Filtering

4. Evidence–Claim Comparison

5. Verdict Assembly



**Rationale**



* Clear state transitions

* Easy to reason about failures

* Avoids opaque agent loops



---



### 2. OpenAI API for Language Reasoning



Used for:



* Sub-claim extraction

* Evidence relevance assessment

* Verdict reasoning



**Rationale**



* Strong instruction adherence

* Better grounding behavior for evidence-based tasks

* Lower implementation risk for MVP



---



### 3. Tavily for Web Search



Used for retrieving candidate sources and original reporting.



**Rationale**



* Search-focused API

* Structured responses

* Faster than custom scraping



---



### 4. Gradio for UI



Gradio will serve as the presentation layer.



**Rationale**



* Minimal frontend complexity

* Rapid iteration

* Suitable for demos and portfolio review

* Clear separation from backend logic



---



## Alternatives Rejected



* Multi-agent debate systems (scope risk)

* React/Next.js frontend (unnecessary complexity)

* Autonomous browsing agents (instability, complexity)



---



## Consequences



### Positive



* Inspectable reasoning

* Easy to explain in interviews

* Small, coherent codebase



### Negative



* Not production-grade

* Limited scalability

* Dependent on external APIs
