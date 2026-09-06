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
- **Zustand State Stores**: `authStore` for user session token, `useReaderStore` for zoom, page, selection, intent, and context state, and `useTutorStore` for Phase 7 study session management.
- **Typed API Client**: Centralized wrapper managing JWT auth headers and unified error handling (`apiClient` & `tutorApi`).

### 2. API Gateway & Application Server (`/backend`)
- **FastAPI Framework**: High-performance async Python backend with automatic Pydantic v2 validation.
- **Security & Authorization**: JWT token verification, document ownership matching, page boundary verification, cross-user conversation isolation, study session isolation, and context injection prevention.
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
- `ContextBuilder`: Multi-layer context engine assembling Active Selection (L1), Page Content (L2), Section Metadata (L3), Chapter Metadata (L4), Rolling Summary (L5), Document Evidence (L6), Recent History (L7), and User Annotations (L8) within configurable token budgets (`CONTEXT_MAX_TOTAL_TOKENS`).
- `RAGService`: Grounded RAG completion with context snapshot telemetry logging and non-blocking background rolling summary updates.
- `HighlightService`: Annotation & highlight management with color filters, notes, bounding boxes, and RAG injection.
- `TutorService`: Phase 7 state machine (CREATED -> ASSESSING -> TEACHING -> QUESTION -> EVALUATING -> FEEDBACK -> COMPLETED), adaptive difficulty calculation, grounded hint generation, flashcard extraction, and quiz evaluation.
- `HybridRetrievalPipeline`: Phase 8 modular retrieval engine comprising `DenseRetriever` (pgvector cosine), `LexicalRetriever` (PostgreSQL `tsvector` + GIN index / regex term matching), `FusionService` (Reciprocal Rank Fusion RRF & deduplication), `RerankerService` (`BaseReranker`, `MockReranker`, `CohereReranker`), and detailed `RetrievalTelemetry`.

### 4. Database Layer (PostgreSQL 16 + pgvector)
- Single PostgreSQL database instance managing relational models and vector embeddings via `pgvector`.
- Async SQLAlchemy 2.0 ORM with Alembic migration version control (current head: `006_real_ai_embedding_dimension`).
- Authoritative page content stored in `document_pages`, searchable vector chunks in `document_chunks` (with pgvector HNSW index and PostgreSQL GIN tsvector index), persistent chat threads/rolling summaries in `conversations` and `chat_messages`, highlights in `highlights`, study sessions in `study_sessions`, flashcards in `study_flashcards`, and quizzes in `study_quizzes`.
- Primary key strategy: Standard UUIDv4 across all tables.


