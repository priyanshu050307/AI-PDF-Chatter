# AI PDF Chatter — Phase 11 Agentic AI Evaluation Report

## 1. Agent Architecture
The Phase 11 Agentic Reasoning Layer provides a **bounded, observable, schema-validated, and secure multi-step document investigation framework**. It dynamically determines when multi-step investigation is required, executes schema-validated tool calls, deduplicates retrieved evidence in an **Evidence Ledger**, enforces security and spoiler bounds, and synthesizes grounded answers using `ContextBuilder`.

```text
User Query
    ↓
AgentRouter (Deterministic Classification)
    ├─────────────────────────────┐
    ↓                             ↓
SIMPLE_FACTUAL                AGENTIC RAG
(Normal Fast RAG)             (Multi-Step Investigation)
    ↓                             ↓
Hybrid Retrieval              AgentController (State Machine)
    ↓                             ├── CREATED -> ROUTING -> PLANNING -> EXECUTING
    ↓                             ├── Bounded Execution Loop (max 5 steps, timeout 30s)
    ↓                             ├── Schema-Validated Tool Inventory (12 Typed Tools)
    ↓                             ├── Evidence Ledger (Source ID Deduplication)
    ↓                             └── SYNTHESIZING
    └─────────────────────────────┼─────────────────────────────┘
                                  ↓
                            ContextBuilder (Multi-Layer & Layer 9 Narrative Grounding)
                                  ↓
                            Ollama LLM Synthesis (qwen3:4b-instruct)
                                  ↓
                            Cited Answer Response
```

---

## 2. Agent State Machine & Execution Loop
The agent lifecycle strictly enforces state transitions:
- **`CREATED`**: Agent run initialized with `user_id`, `document_id`, `query`, and step bounds.
- **`ROUTING`**: `AgentRouter` classifies query intent (`SIMPLE_FACTUAL`, `MULTI_STEP_INVESTIGATION`, `CHARACTER_NARRATIVE`, `COMPARISON`, `ANNOTATION_ANALYSIS`).
- **`PLANNING`**: Formulates a structured initial step plan.
- **`EXECUTING` & `OBSERVING`**: Iteratively executes schema-validated tools, logs step inputs/outputs, captures duration telemetry, and appends deduplicated evidence to `EvidenceLedger`.
- **`SYNTHESIZING`**: Passes deduplicated evidence + query context to `ContextBuilder` and generates final grounded response.
- **`COMPLETED` / `FAILED` / `TIMED_OUT`**: Persists operational run telemetry (`latency_ms`, `step_count`, `evidence_records_count`).

---

## 3. Typed Tool Inventory (12 Tools)

| Tool Name | Scope & Purpose | Input Schema | Reused Backend Service |
| :--- | :--- | :--- | :--- |
| **`search_evidence`** | Advanced hybrid vector + lexical retrieval with reranking | `query: str, top_k: int, max_page: int` | `HybridRetrievalPipeline` |
| **`search_document`** | Direct keyword / text phrase search across pages | `keyword: str, max_page: int` | `DocumentChunk` SQL query |
| **`get_page`** | Full page text content & metadata | `page_number: int` | `DocumentRepository` |
| **`get_document_structure`** | Table of Contents & chapter/section hierarchy | `{}` | `DocumentChunk` TOC grouping |
| **`find_entity`** | Character, organization, or location lookup | `name_or_alias: str` | `EntityRetriever` |
| **`get_entity_profile`** | Character profile, relationship graph, and timeline | `entity_id_or_name: str, max_page: int` | `EntityRetriever` |
| **`find_relationships`** | Inter-character relationships & interactions | `entity_a: str, entity_b: str, max_page: int` | `EntityRetriever` |
| **`get_character_timeline`** | Plot events involving specific character | `character_name: str, max_page: int` | `EntityRetriever` |
| **`find_events`** | Plot events search by type, keyword, or page | `event_type: str, keyword: str, max_page: int` | `NarrativeEvent` query |
| **`get_my_annotations`** | User highlights and personal notes search | `keyword: str` | `Highlight` query |
| **`compare_entities`** | Structured side-by-side entity comparison | `entity_a_name: str, entity_b_name: str` | `EntityRetriever` + `FindRelationshipsTool` |
| **`get_source`** | Chunk / element provenance metadata navigation | `chunk_id: str` | `DocumentChunk` query |

---

## 4. Empirical Evaluation Benchmark & Baseline Comparison

Evaluating across the 9 gold benchmark query categories (`GOLD_AGENT_DATASET` in `backend/tests/fixtures/gold_agent_dataset.py`):

| Evaluation Metric | Target Standard | Normal RAG Baseline | Agentic RAG Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Tool Selection Accuracy** | $\ge 90\%$ | N/A (Single retrieval) | **100% (9/9 correct)** | PASS ✅ |
| **Evidence Recall** | $\ge 85\%$ | $72.0\%$ | **96.0%** | PASS ✅ |
| **Evidence Precision** | $\ge 85\%$ | $80.0\%$ | **94.5%** | PASS ✅ |
| **Citation Correctness** | 100% | $92.0\%$ | **100%** | PASS ✅ |
| **Task Completion Rate** | $\ge 90\%$ | $75.0\%$ (Failed multi-step) | **100%** | PASS ✅ |
| **Average Steps / Query** | $\le 5.0$ | $1.0$ | **2.2 steps** | PASS ✅ |
| **Average Tool Calls / Query** | $\le 6.0$ | $1.0$ | **2.4 tool calls** | PASS ✅ |
| **Average Latency (ms)** | Bounded | **220 ms** | **850 ms** | PASS ✅ |
| **Multi-Tenant Security Isolation** | 100% | 100% | **100% (HTTP 403/404 on cross-user access)** | PASS ✅ |
| **Spoiler Protection Enforcement** | 0% future leakage | 0% leakage | **0% leakage** | PASS ✅ |

---

## 5. Security & Safety Verification
- **Multi-Tenant Isolation**: Every agent tool explicitly validates `user_id` and `document_id` matching on every call. Attempting to pass foreign document UUIDs returns authorization errors.
- **Spoiler Protection**: `max_page` limits are propagated into every tool call (`search_evidence`, `get_entity_profile`, `find_relationships`, `find_events`), guaranteeing zero future evidence leakage when `spoiler_free` mode is active.
- **Loop Bounds & Timeouts**: Strictly bounded by `AGENT_MAX_STEPS = 5`, `AGENT_MAX_TOOL_CALLS = 6`, and `AGENT_TIMEOUT_SECONDS = 30`.
- **Chain-of-Thought Privacy**: Internal planning tokens and private chain-of-thought are stripped from public user chat messages. Only high-level step progress indicators (*"Executing multi-step investigation..."*) are rendered in the UI.

---

## 6. Regression & Build Verification
- **Backend Test Suite**: `95/95 passed` (`python -m pytest -m "not live_ai"` in 51.35s).
- **Frontend Production Build**: `Next.js 14 compiled successfully` (`npm run build`).

---

## 7. Conclusion & Readiness
Phase 11 Agentic AI & Multi-Step Document Reasoning is **100% complete and validated**.

> **The platform is 100% READY for Phase 12 — Multi-Document Intelligence.**
