# AI PDF Chatter — Architecture Overview

## Overview
AI PDF Chatter is designed as a decoupled, multi-tier system built for high scalability, real-time AI streaming, context-aware reading, persistent conversation memory, and multi-document reasoning.

## Architecture Layers

### 1. Client Layer (`/frontend`)
- **Next.js 14 (App Router)**: Rendered client-side and server-side components.
- **PDF Viewer & Selection Engine (`PdfReader`)**: Client-side text selection detection (`mouseup`), coordinate calculation, and active selection state tracking.
- **Selection Toolbar (`SelectionToolbar`)**: Floating contextual toolbar for intent actions (`Explain`, `Simplify`, `Example`, `Ask AI`).
- **Conversation Drawer & List (`ConversationList`)**: Slide-out drawer displaying user chat threads for the current document, featuring inline title editing, deletion, and "+ New Chat" workflows.
- **Chat Panel (`ChatPanel`)**: Active context indicator bar displaying current page, section, chapter, active selection snippet, "Clear Context ×" control, and paginated message history loading.
- **AI Study Workspace (`StudyWorkspace`)**: Phase 7 unified container featuring tabbed views for AI Tutor Card, Flashcard Deck, Quiz Runner, and Study History.
- **AI Tutor Card (`TutorCard`)**: Interactive concept breakdown, diagnostic assessment, progressive hints, and adaptive difficulty adjustment.
- **3D Flashcard Deck (`FlashcardDeck`)**: CSS 3D flip card recall deck with rating controls (Again/Hard/Good/Easy) and page citations.
- **Comprehension Quiz Runner (`QuizRunner`)**: Multi-format quiz runner (MCQ, True/False, Short Answer) with automatic grading and citation reporting.
- **Evaluation Dashboard UI (`/evaluations`)**: Phase 13 evaluation dashboard featuring system metric cards (Recall@K, Faithfulness, Citations, Agent Efficiency, Spoiler Leakage, P95 Latency), run selector, Model A vs Model B side-by-side experiment comparison matrix, sample-level debugging drawer, and human review labeling.
- **Zustand State Stores**: `authStore` for user session token, `useReaderStore` for zoom, page, selection, intent, and context state, `useTutorStore` for Phase 7 study session management, `useWorkspaceStore` for Phase 12 workspace collections, and `useEvalStore` for Phase 13 evaluation runs and metrics.
- **Typed API Client**: Centralized wrapper managing JWT auth headers and unified error handling (`apiClient`, `tutorApi`, `workspaceApi`, and `evalApi`).

### 2. API Gateway & Application Server (`/backend`)
- **FastAPI Framework**: High-performance async Python backend with automatic Pydantic v2 validation.
- **Security & Authorization**: JWT token verification, document ownership matching, page boundary verification, cross-user conversation isolation, study session isolation, workspace document ownership isolation (`workspace.user_id == document.user_id`), evaluation run ownership isolation, and context injection prevention.
- **Layered Clean Architecture**:
  ```text
  Route Handler -> Schema Validation -> Service Layer -> Repository Data Access -> Database Model
  ```

### 3. Service Layer & AI Pipeline Abstractions
- `AuthService`: Password hashing (passlib/bcrypt) and JWT user sessions.
- `StorageService`: Pluggable object storage interface supporting local filesystem storage, MinIO, and AWS S3/Cloudflare R2.
- `DocumentProcessingService`: PDF text parsing, structural hierarchy detection, and page extraction (PyMuPDF).
- `EmbeddingService`: Vector generation (Ollama `embeddinggemma` 768-dim / OpenAI `text-embedding-3-small` / mock).
- `RetrievalService`: Selection-aware pgvector similarity search with fallback math for SQLite.
- `ConversationMemoryService`: Manages persistent history, bounded recent memory selection (`CONVERSATION_MAX_HISTORY_TOKENS`), rolling summaries, token budgeting, and follow-up pronoun reference resolution.
- `ContextBuilder`: Multi-layer context engine assembling Active Selection (L1), Page Content (L2), Section Metadata (L3), Chapter Metadata (L4), Rolling Summary (L5), Document Evidence (L6), Recent History (L7), User Annotations (L8), Narrative Graph & Character Context (L9), and Document Title Source Headers & Multi-Doc Citations (Phase 12) within configurable token budgets (`CONTEXT_MAX_TOTAL_TOKENS`).
- `HighlightService`: Annotation & highlight management with color filters, notes, bounding boxes, and RAG injection.
- `TutorService`: Phase 7 state machine (CREATED -> ASSESSING -> TEACHING -> QUESTION -> EVALUATING -> FEEDBACK -> COMPLETED), adaptive difficulty calculation, grounded hint generation, flashcard extraction, and quiz evaluation.
- `HybridRetrievalPipeline`: Phase 8 modular retrieval engine comprising `DenseRetriever` (pgvector cosine), `LexicalRetriever` (PostgreSQL `tsvector` + GIN index / regex term matching), `FusionService` (Reciprocal Rank Fusion RRF & deduplication), `RerankerService` (`BaseReranker`, `MockReranker`, `CohereReranker`), detailed `RetrievalTelemetry`, Phase 9 multimodal query routing (`table_question`, `visual_question`), and Phase 12 document-balanced multi-document candidate retrieval (`document_ids: Optional[List[UUID]]`).
- `BaseOCRProvider`: Phase 9 OCR abstraction (`MockOCRProvider`, `PyMuPDFOCRProvider`, `TesseractOCRProvider`) supporting scanned page detection and OCR text extraction.
- `BaseVisionProvider`: Phase 9 Multimodal Vision model abstraction (`MockVisionProvider`, `OllamaVisionProvider`, `DisabledVisionProvider`) generating visual summaries for extracted figures and diagrams.
- `NarrativeExtractor`: Phase 10 zero-dependency entity classifier (`PERSON`, `LOCATION`, `ORGANIZATION`, `EVENT`), character importance ranker (`major`, `minor`, `background`), alias normalizer, coreference resolver, relationship extractor (`trusts`, `enemy_of`, `family_with`, etc.), and timeline event builder.
- `EntityRetriever`: Phase 10 graph retrieval engine performing bounded 1-hop / 2-hop / 3-hop graph traversal and page-capping spoiler protection (`spoiler_free`, `current_position`, `full_book`).
- `AgentController`: Phase 11 agent execution engine and state machine (`CREATED` -> `ROUTING` -> `PLANNING` -> `EXECUTING` -> `OBSERVING` -> `SYNTHESIZING` -> `COMPLETED`) managing bounded step loops (`AGENT_MAX_STEPS = 5`), timeout protection (`30s`), and evidence synthesis.
- `AgentRouter`: Phase 11 deterministic classifier routing queries between Normal Fast RAG (`SIMPLE_FACTUAL`) and Agentic Multi-Step Investigation (`AGENTIC_RAG`, `CHARACTER_NARRATIVE`, `COMPARISON`, `ANNOTATION_ANALYSIS`, `MULTI_DOC_*`).
- `EvidenceLedger`: Phase 11 deduplicated evidence accumulator storing structured tool observations by source ID.
- `BaseAgentTool`: Typed tool framework exposing 17 schema-validated tools (12 Phase 11 single-doc tools + 5 Phase 12 multi-doc tools: `search_workspace`, `compare_documents`, `find_common_claims`, `find_conflicting_claims`, `get_document_evidence`).
- `MultiDocService`: Phase 12 engine powering cross-document comparison (`compare_documents`), consensus identification (`find_common_claims`), contradiction detection with experimental condition preservation (`find_conflicting_claims`), and directed claim-evidence graph generation (`build_claim_evidence_graph`).
- `EvaluationRunner`: Phase 13 orchestrator executing standardized versioned datasets (`retrieval-v1`, `agent-v1`, `narrative-v1`, `multidoc-v1`, `multimodal-v1`, `tutor-v1`, `hallucination-v1`), calculating quality/latency metrics, evaluating Quality Gates (`MIN_RECALL_AT_5`, `MIN_CITATION_CORRECTNESS`, `MAX_P95_LATENCY`, `MAX_FAILURE_RATE`), wrapping LLM-as-a-Judge safety, and exporting JSON/Markdown reports.

### 4. Database Layer (PostgreSQL 16 + pgvector)
- Single PostgreSQL database instance managing relational models and vector embeddings via `pgvector`.
- Async SQLAlchemy 2.0 ORM with Alembic migration version control (current head: `011_phase13_evaluation`).
- Authoritative page content stored in `document_pages`, extracted tables/figures/OCR elements in `document_elements`, searchable vector chunks in `document_chunks` (with pgvector HNSW index and PostgreSQL GIN tsvector index), persistent chat threads/rolling summaries in `conversations` and `chat_messages`, highlights in `highlights`, study sessions in `study_sessions`, flashcards in `study_flashcards`, quizzes in `study_quizzes`, characters/entities in `entities`, graph relationships in `entity_relationships`, narrative timeline in `narrative_events`, agent runs in `agent_runs`, step traces in `agent_steps`, multi-document collections in `workspaces`, collection document links in `workspace_documents`, evaluation runs in `eval_runs`, sample-level debugging cases in `eval_case_results`, and human reviews in `eval_human_reviews`.
- Primary key strategy: Standard UUIDv4 across all tables.

### 5. Production Infrastructure, Security & Reliability (Phase 14)
- **Containerization Engine (`Dockerfile.frontend`, `Dockerfile.backend`, `Dockerfile.worker`)**: Multi-stage production Docker images optimized for minimal layer size and non-root execution (`nextjs` / `fastapi` system users).
- **Reverse Proxy Gateway (`nginx/nginx.conf`)**: Production Nginx container enforcing TLS termination, HTTP security headers (`nosniff`, `DENY`, `strict-origin-when-cross-origin`), client body upload ceiling (`500M`), SSE streaming headers (`X-Accel-Buffering: no`), and private network boundary protection blocking external exposure of Ollama port 11434 (`/ollama/` returns 403 Forbidden).
- **Correlation ID Middleware (`CorrelationIDMiddleware`)**: Automatic generation and propagation of `X-Correlation-ID` across distributed request contexts for end-to-end trace log correlation.
- **Sliding-Window Rate Limiter (`check_rate_limit`)**: Redis-backed sliding window rate limiter (`rate_limit:{key}`) enforcing configurable burst limits for document upload (10 req/min) and AI chat endpoints (60 req/min), degrading gracefully if Redis is unavailable.
- **File Upload Security Engine**: Strict `%PDF-` magic header signature verification, MIME validation, and file size capping preventing malicious non-PDF upload attacks.
- **Untrusted Evidence Defense**: ContextBuilder prompt engineering isolating retrieved PDF excerpts as untrusted external evidence, instructing LLMs to ignore embedded prompt injection commands.
- **Operational Health & Probes**: `/health/liveness` probe for container orchestrator restart signals, `/health/readiness` probe for PostgreSQL/Redis readiness, and `/monitoring/health` router providing real-time system metrics (CPU, RAM, uptime, DB pool, Redis status).



