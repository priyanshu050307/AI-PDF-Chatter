# AI PDF Chatter — Product & Engineering Roadmap

## Phased Implementation Schedule

- **Phase 0 — Product & Architecture Foundation** `[COMPLETED]`
  - Baseline project setup, FastAPI backend, Async SQLAlchemy, Alembic migrations, JWT Auth, storage abstraction, Celery Redis worker queue structure, Next.js frontend shell, test suites, and documentation.

- **Phase 1 — PDF Library + Viewer**
  - Document upload API, storage persistence, PDF dashboard grid, PDF.js reader integration with page navigation and reading progress save.

- **Phase 2 — PDF Processing Pipeline**
  - Background layout analysis (PyMuPDF/pdfplumber), page representation, context-aware text chunking, and embedding generation into `pgvector`.

- **Phase 3 — Basic RAG Chat**
  - Vector similarity search over PDF chunks, citation generation, and standard LLM chat completion.

- **Phase 4 — Context-Aware Reading**
  - Selection engine capturing highlighted text, page context, section context, and current reading location.

- **Phase 5 — Conversation Memory**
  - Multi-turn conversation persistence, context memory, and conversation history APIs.

- **Phase 6 — Notes, Highlights & Annotations**
  - User text highlighting, offset persistence, inline notes, and AI query integration over user annotations.

- **Phase 7 — AI Study / Learning Mode**
  - Dedicated tutor prompts ("Teach Me", Quizzes, Summaries, Progressive explanations).

- **Phase 8 — Advanced Retrieval System**
  - Hybrid search (Vector + Keyword tsvector) + Cohere Reranking.

- **Phase 9 — Document Intelligence & OCR**
  - Scanned PDF support (Tesseract OCR), table extraction, and multi-modal image processing.

- **Phase 10 — Novel & Character Intelligence**
  - Graph entity extraction (Characters, Relationships, Events, Locations, Timelines).

- **Phase 11 — Agentic PDF Assistant**
  - ReAct multi-step planning agent for complex comparative queries.

- **Phase 12 — Multi-Document Intelligence** `[COMPLETED]`
  - Workspaces & collections, document-balanced hybrid retrieval, attributed cross-doc RAG, claim comparison, consensus finding, contradiction engine preserving experimental conditions, 5 multi-doc agent tools, and Research Workspace UI.


- **Phase 13 — Evaluation & AI Quality Engineering** `[COMPLETED]`
  - Unified multi-dimensional evaluation runner, dataset versioning (`retrieval-v1`, `agent-v1`, `narrative-v1`, `multidoc-v1`, `multimodal-v1`, `tutor-v1`, `hallucination-v1`), Quality Gates checks, P50/P95/P99 latency calculations, LLM-as-a-Judge safety, developer CLI (`python -m app.eval`), and Next.js Evaluation Dashboard (`/evaluations`).


- **Phase 14 — Production Engineering & Scalability** `[COMPLETED]`
  - Production multi-stage Docker builds (`Dockerfile.frontend`, `Dockerfile.backend`, `Dockerfile.worker`), Nginx reverse proxy gateway with TLS termination, security headers (`nosniff`, `DENY`, `strict-origin-when-cross-origin`), private boundary protection blocking external exposure of Ollama port 11434, Redis sliding-window rate limiting, correlation ID propagation (`X-Correlation-ID`), strict `%PDF-` magic header file upload validation, untrusted document evidence prompt injection defense, health probes (`/health/liveness`, `/health/readiness`), operational monitoring router (`/api/v1/monitoring/health`), operational runbook (`docs/production-runbook.md`), 69-point readiness audit checklist (`docs/production-readiness-checklist.md`), and Phase 14 test suite (`test_production_hardening.py`).
