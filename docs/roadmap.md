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

- **Phase 12 — Multi-Document Intelligence**
  - Cross-document retrieval and synthesis across multiple PDF libraries.

- **Phase 13 — Evaluation & AI Quality Engineering**
  - Benchmarking runner evaluating Recall@K, Faithfulness, latency, and token cost metrics.

- **Phase 14 — Production Engineering & Scalability**
  - Rate limiting, Redis caching layer, CDN storage integration, and load balancing configurations.
