# AI PDF Chatter — Context-Aware Intelligent Reading Workspace

[![Architecture Spec](https://img.shields.io/badge/Architecture-Specification-blue)](./ARCHITECTURE_SPEC.md)
[![Phase Roadmap](https://img.shields.io/badge/Phase_14-Production_Scaling_Completed-brightgreen)](#phased-roadmap-summary)

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
- **AI Abstraction:** LiteLLM / Ollama (`qwen3:4b-instruct`, `embeddinggemma`) / OpenAI / Anthropic / Cohere Reranker

---

## 🚀 Phased Roadmap Summary

| Build Iteration | Target Phases | Key Deliverables | Status |
| :--- | :--- | :--- | :--- |
| **Milestone 1: MVP Baseline** | Phase 0 - Phase 3 | Core setup, PDF Library, PDF Reader (PDF.js), Chunking pipeline, Basic Vector RAG chat with citations. | **Completed** ✅ |
| **Milestone 2: Context Reader & Memory** | Phase 4 - Phase 5 | Multi-layer context selection, Persistent conversation memory, rolling summaries, history pagination, thread switching. | **Completed** ✅ |
| **Milestone 3: Annotations, Tutor & RAG Quality** | Phase 6 - Phase 8 | Highlights & notes, AI Tutor mode (Flashcards, Quizzes, Hints), Modular Hybrid Retrieval (pgvector + tsvector + RRF + Cohere/Mock Reranker), Retrieval Telemetry & Evaluation Benchmark. | **Completed** ✅ |
| **Real Local AI Integration** | Local AI Stack | End-to-end integration with local Ollama runtime (`qwen3:4b-instruct` LLM & `embeddinggemma` 768-dim embeddings). Real PDF ingestion, real vector retrieval, real RAG, conversation memory, annotation AI, and Tutor mode. | **Completed** ✅ |
| **Milestone 4: Scanned OCR & Multimodal** | Phase 9 | Scanned page detection & OCR fallback, PyMuPDF structured table extraction, figure/image extraction, Vision provider abstraction (`MockVisionProvider`, `OllamaVisionProvider`), Multimodal Hybrid Retrieval, and ContextBuilder citations (`[Page X, Table Y]`, `[Page X, Figure Y]`). | **Completed** ✅ |
| **Milestone 5: Narrative Intelligence** | Phase 10 | Character & entity graph extraction (`PERSON`, `LOCATION`, `ORGANIZATION`, `EVENT`), alias normalization, coreference resolution, temporal relationship tracking (`trusts`, `enemy_of`, etc.), narrative event timeline, graph retrieval engine, spoiler protection (`spoiler_free`, `current_position`, `full_book`), and interactive Character Panel UI. | **Completed** ✅ |
| **Milestone 6: Agent Intelligence** | Phase 11 | Bounded Agent Controller state machine, 12 typed schema-validated tools, Evidence Ledger deduplication, deterministic AgentRouter, spoiler-safe multi-step reasoning, entity comparison, annotation analysis, and Deep Analysis UI. | **Completed** ✅ |
| **Milestone 7: Multi-Doc Intelligence** | Phase 12 | Research Workspaces & collections, document-balanced hybrid retrieval, attributed cross-doc RAG, claim comparison, consensus finding, contradiction detection with experimental condition preservation, 5 multi-doc agent tools, and Research Workspace UI. | **Completed** ✅ |
| **Milestone 8: Unified Evaluation** | Phase 13 | Multi-dimensional benchmark framework (Retrieval, Generation, Citations, Agents, Narrative, Multimodal, Tutor, Hallucinations), Quality Gates, P50/P95/P99 latencies, developer CLI (`python -m app.eval`), and Next.js Evaluation Dashboard (`/evaluations`). | **Completed** ✅ |
| **Milestone 9: Production Scaling & Reliability** | Phase 14 | Production Docker multi-stage images, reverse proxy Nginx gateway with TLS & security headers, Redis rate limiting, correlation IDs, file upload %PDF- magic signature validation, untrusted evidence defenses, health probes (`/health/liveness`, `/health/readiness`), and operational monitoring router (`/api/v1/monitoring/health`). | **Completed** ✅ |





