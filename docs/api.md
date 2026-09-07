# AI PDF Chatter — API Specification (v1)

## Base URL
`/api/v1`

## Error Response Format
All error responses follow a standard structure:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Context document_id does not match the conversation document.",
    "details": null
  }
}
```

## Endpoints Summary

### System Health & Operational Monitoring (Phase 14)
- **`GET /api/v1/health`**: General system health check.
- **`GET /api/v1/health/liveness`**: Container liveness probe (200 OK).
- **`GET /api/v1/health/readiness`**: Infrastructure readiness probe (PostgreSQL, Redis).
- **`GET /api/v1/monitoring/health`**: Operational infrastructure metrics (Uptime, CPU/RAM, DB Pool status, Redis connection status).

### Authentication
- **`POST /api/v1/auth/signup`**
- **`POST /api/v1/auth/login`**
- **`GET /api/v1/users/me`**

### Document Library & Processing
- **`POST /api/v1/documents`**: Upload PDF document.
- **`GET /api/v1/documents`**: List user's documents.
- **`GET /api/v1/documents/{id}`**: Get document status & progress.
- **`POST /api/v1/documents/{id}/process`**: Process document pipeline.

### Conversation Memory & Chat (Phase 5)
- **`POST /api/v1/documents/{id}/conversations`**: Create new chat thread.
- **`GET /api/v1/documents/{id}/conversations`**: List all user conversations for a document.
- **`GET /api/v1/conversations/{id}`**: Get specific conversation details, rolling summary, and recent messages.
- **`PATCH /api/v1/conversations/{id}`**: Rename conversation title.
  - Body: `{"title": "Renamed Discussion Title"}`
- **`DELETE /api/v1/conversations/{id}`**: Delete conversation and cascading messages (`204 No Content`).
- **`GET /api/v1/conversations/{id}/messages`**: Paginated message history.
  - Query Params: `limit` (default: 50), `before` (UUID cursor).
  - Response:
    ```json
    {
      "items": [...],
      "total": 14,
      "has_more": false,
      "next_cursor": null
    }
    ```
- **`POST /api/v1/conversations/{id}/messages`**: Send context-aware message.
  - Telemetry response includes `history_messages_used`, `history_tokens_used`, `summary_used`, `summary_tokens`, and performance latencies.

### Highlights & Annotations (Phase 6)
- **`GET /api/v1/documents/{id}/highlights`**: List document highlights (filters: `page_number`, `color`, `has_note`, `search`).
- **`POST /api/v1/documents/{id}/highlights`**: Create new highlight annotation with bounding box and note.
- **`PATCH /api/v1/highlights/{id}`**: Update highlight color or note text.
- **`DELETE /api/v1/highlights/{id}`**: Delete highlight annotation (`204 No Content`).

### AI Study & Tutor Mode (Phase 7)
- **`POST /api/v1/tutor/sessions`**: Create guided study session (`document_id`, `difficulty`, `learning_goal`, `topic_scope`).
- **`GET /api/v1/tutor/sessions`**: List study sessions for a document (`document_id`).
- **`GET /api/v1/tutor/sessions/{id}`**: Get study session state machine details & history.
- **`DELETE /api/v1/tutor/sessions/{id}`**: Delete study session (`204 No Content`).
- **`POST /api/v1/tutor/sessions/{id}/turn`**: Process tutor state machine turn (`action`: `START` | `ANSWER` | `NEXT_CONCEPT` | `RETRY`).
- **`GET /api/v1/tutor/sessions/{id}/hint`**: Request progressive grounded hint (Level 1, 2, 3).
- **`GET /api/v1/tutor/sessions/{id}/summary`**: Generate study session performance summary.
- **`POST /api/v1/tutor/flashcards/generate`**: Generate grounded AI flashcards deck (`count`, `document_id`, `session_id`).
- **`GET /api/v1/tutor/flashcards`**: List flashcards (`document_id`, `session_id`).
- **`POST /api/v1/tutor/flashcards/{id}/rate`**: Rate flashcard difficulty (`AGAIN` | `HARD` | `GOOD` | `EASY`).
- **`POST /api/v1/tutor/quizzes/generate`**: Generate comprehension quiz (`question_count`, `document_id`, `session_id`).
- **`GET /api/v1/tutor/quizzes/{id}`**: Get quiz details.
- **`POST /api/v1/tutor/quizzes/{id}/submit`**: Submit quiz answers for automated evaluation & citation reporting.

### Advanced Retrieval & RAG Quality (Phase 8)
- **`POST /api/v1/documents/{document_id}/retrieval/debug`**: Inspect candidate scoring across Dense Vector, Lexical Full-Text, Reciprocal Rank Fusion (RRF), and Reranker steps.
  - Body: `{"query": "CVE-2026-1234 security", "top_k": 5, "selected_text": "optional highlight context"}`
  - Response:
    ```json
    {
      "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "query": "CVE-2026-1234 security",
      "dense_candidates": [...],
      "lexical_candidates": [...],
      "fused_candidates": [...],
      "final_results": [...],
      "telemetry": {
        "query_normalized": "cve 2026 1234 security",
        "dense_candidates_count": 5,
        "lexical_candidates_count": 5,
        "fused_candidates_count": 8,
        "reranked_candidates_count": 5,
        "dense_retrieval_ms": 12.4,
        "lexical_retrieval_ms": 8.1,
        "fusion_ms": 1.2,
        "rerank_ms": 4.5,
        "total_retrieval_ms": 26.2
      }
    }
    ```

### Multimodal PDF Intelligence (Phase 9)
- **`GET /api/v1/documents/{document_id}/elements`**: List all extracted multimodal elements (tables, figures, OCR regions) for document.
  - Query Params: `element_type` (`table` | `image` | `ocr_text`).
  - Response:
    ```json
    [
      {
        "id": "c1f7a8b2-3d4e-4f5a-6b7c-8d9e0f1a2b3c",
        "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "page_number": 4,
        "element_type": "table",
        "bbox_json": {"x0": 50.0, "y0": 100.0, "x1": 500.0, "y1": 300.0},
        "content": "| Header 1 | Header 2 |\n| --- | --- |\n| Value 1 | Value 2 |",
        "structured_data": {"headers": ["Header 1", "Header 2"], "rows": [["Value 1", "Value 2"]]},
        "ocr_confidence": null,
        "created_at": "2026-09-07T12:00:00Z"
      }
    ]
    ```
- **`GET /api/v1/documents/{document_id}/elements/{element_id}/image`**: Stream extracted PNG figure asset.

### Character & Narrative Intelligence (Phase 10)
- **`GET /api/v1/documents/{document_id}/narrative/entities`**: List characters and entities (filters: `importance` = `major` | `minor` | `background`).
- **`GET /api/v1/documents/{document_id}/narrative/entities/{entity_id}`**: Get character profile, relationship graph, and timeline (query param: `max_page`).
- **`GET /api/v1/documents/{document_id}/narrative/timeline`**: Get ordered narrative event timeline (query param: `max_page`).
- **`POST /api/v1/documents/{document_id}/narrative/ask`**: Execute graph RAG answer generation with spoiler control (`spoiler_free`, `current_position`, `full_book`).

### Agentic AI & Multi-Step Reasoning (Phase 11)
- **`POST /api/v1/documents/{document_id}/agent/ask`**: Execute bounded Agentic AI multi-step document investigation.
  - Body: `{"query": "Compare Lord Sterling and Lady Eleanor Vance", "mode": "auto", "spoiler_mode": "spoiler_free", "current_page": 5}`
  - Response:
    ```json
    {
      "run_id": "c1f7a8b2-3d4e-4f5a-6b7c-8d9e0f1a2b3c",
      "query": "Compare Lord Sterling and Lady Eleanor Vance",
      "answer": "Grounded comparative synthesis...",
      "route": "COMPARISON",
      "state": "COMPLETED",
      "steps": [
        {"step": 1, "tool": "compare_entities", "description": "Executed compare_entities", "status": "COMPLETED", "duration_ms": 12.4},
        {"step": 2, "tool": "search_evidence", "description": "Executed search_evidence", "status": "COMPLETED", "duration_ms": 18.1}
      ],
      "citations": [...],
      "latency_ms": 420.5
    }
    ```
- **`GET /api/v1/documents/{document_id}/agent/runs/{run_id}`**: Retrieve high-level agent run status, operational telemetry, and step trace.

### Multi-Document Intelligence & Research Workspaces (Phase 12)
- **`GET /api/v1/workspaces`**: List current user's research workspaces.
- **`POST /api/v1/workspaces`**: Create a new research workspace collection (`title`, `description`).
- **`GET /api/v1/workspaces/{id}`**: Get workspace details and attached document list.
- **`DELETE /api/v1/workspaces/{id}`**: Delete workspace container (`204 No Content`).
- **`POST /api/v1/workspaces/{id}/documents`**: Attach user document to workspace (`document_id`).
- **`DELETE /api/v1/workspaces/{id}/documents/{document_id}`**: Remove document from workspace collection (`204 No Content`).
- **`POST /api/v1/workspaces/{id}/query`**: Execute cross-document attributed RAG query across selected workspace PDFs (`query`, `selected_document_ids`).
- **`POST /api/v1/workspaces/{id}/compare`**: Side-by-side comparative analysis of selected documents on a topic (`topic`, `selected_document_ids`).
- **`POST /api/v1/workspaces/{id}/agreements`**: Detect common agreed claims across selected documents (`topic`, `selected_document_ids`).
- **`POST /api/v1/workspaces/{id}/conflicts`**: Detect contradictions across selected documents preserving experimental conditions (`topic`, `selected_document_ids`).

### Unified AI Evaluation & Quality Engineering (Phase 13)
- **`GET /api/v1/evaluations/datasets`**: List versioned benchmark datasets (`retrieval-v1`, `agent-v1`, `narrative-v1`, `multidoc-v1`, `multimodal-v1`, `tutor-v1`, `hallucination-v1`).
- **`POST /api/v1/evaluations/run`**: Trigger an async evaluation run (`dataset_version`, `llm_provider`, `llm_model`, `limit`).
- **`GET /api/v1/evaluations`**: List evaluation runs for user / public benchmarks.
- **`GET /api/v1/evaluations/{id}`**: Get evaluation run summary, quality gate results, and latency P50/P95/P99.
- **`GET /api/v1/evaluations/{id}/cases`**: List sample-level debugging cases for an evaluation run (`category`, `passed`).
- **`GET /api/v1/evaluations/compare`**: Side-by-side comparison of 2 evaluation runs (`run_id_a`, `run_id_b`).
- **`POST /api/v1/evaluations/cases/{case_id}/review`**: Record human review label (`label`, `notes`).
- **`GET /api/v1/evaluations/{id}/report`**: Download Markdown or JSON evaluation report (`format`).






