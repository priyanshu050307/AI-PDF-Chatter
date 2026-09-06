# AI PDF Chatter — Context-Aware Intelligent Reading Workspace

[![Architecture Spec](https://img.shields.io/badge/Architecture-Specification-blue)](./ARCHITECTURE_SPEC.md)
[![Phase Roadmap](https://img.shields.io/badge/Phase_5-Conversation_Memory_Completed-brightgreen)](#phased-roadmap-summary)

AI PDF Chatter is a modern, context-aware reading companion and AI tutor designed to convert static PDF documents into an interactive, multi-layered knowledge intelligence platform.

---

## 🏗️ System Blueprint & Core Architecture

For the complete technical specifications, database DDL schema, service flow diagrams, and directory structure, refer to the [System Architecture Specification](./ARCHITECTURE_SPEC.md).

### Core Tech Stack
- **Frontend:** Next.js 14 (App Router, React 18, TypeScript), PDF.js, Tailwind CSS, Zustand, TanStack Query
- **Backend API:** Python 3.11 + FastAPI, Async SQLAlchemy 2.0, Alembic, Pydantic v2
- **Vector DB & Database:** PostgreSQL 16 with `pgvector` (HNSW indexing)
- **Background Tasks:** Redis 7 + Celery / ARQ
- **PDF Extraction & NLP:** PyMuPDF (fitz), pdfplumber, Tesseract OCR, SpaCy
- **AI Abstraction:** LiteLLM / OpenAI / Anthropic / Cohere Reranker

---

## 🚀 Phased Roadmap Summary

| Build Iteration | Target Phases | Key Deliverables | Status |
| :--- | :--- | :--- | :--- |
| **Milestone 1: MVP Baseline** | Phase 0 - Phase 3 | Core setup, PDF Library, PDF Reader (PDF.js), Chunking pipeline, Basic Vector RAG chat with citations. | **Completed** ✅ |
| **Milestone 2: Context Reader & Memory** | Phase 4 - Phase 5 | Multi-layer context selection, Persistent conversation memory, rolling summaries, history pagination, thread switching. | **Completed** ✅ |
| **Milestone 3: Annotations, Tutor & RAG Quality** | Phase 6 - Phase 8 | Highlights & notes, AI Tutor mode (Flashcards, Quizzes, Hints), Modular Hybrid Retrieval (pgvector + tsvector + RRF + Cohere/Mock Reranker), Retrieval Telemetry & Evaluation Benchmark. | **Completed** ✅ |
| **Real Local AI Integration** | Local AI Stack | End-to-end integration with local Ollama runtime (`qwen3:4b-instruct` LLM & `embeddinggemma` 768-dim embeddings). Real PDF ingestion, real vector retrieval, real RAG, conversation memory, annotation AI, and Tutor mode. | **Completed** ✅ |
| **Milestone 4: Scanned OCR & Multimodal** | Phase 9 | Scanned PDF OCR pipeline (Tesseract/pdf2image), page image chunking, visual layout table parsing. | Planned ⏳ |
| **Milestone 5: Novel & Agent Intelligence** | Phase 10 - Phase 12 | Character relationship entity graphs, ReAct multi-step agentic analysis, Multi-document querying. | Planned ⏳ |
| **Milestone 6: Production & Benchmarking** | Phase 13 - Phase 14 | Automated RAG evaluation (Recall, Faithfulness), Redis caching, rate limiting, and containerized scale. | Planned ⏳ |
