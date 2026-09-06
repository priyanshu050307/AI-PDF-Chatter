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

### System Health
- **`GET /api/v1/health`**

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


