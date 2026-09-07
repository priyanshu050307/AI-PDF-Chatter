# AI PDF Chatter — Development Guide

## Local Development Prerequisites
- Python 3.11+
- Node.js 18+ & npm / pnpm
- Docker & Docker Compose

## Quick Setup

### 1. Environment Setup
Copy the example environment file:
```bash
cp .env.example .env
```

### 2. Infrastructure Services (Docker)
Start PostgreSQL (pgvector), Redis, and MinIO:
```bash
docker-compose up -d
```

### 3. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. Memory Configuration & Testing (Phase 5)
Memory configuration settings in `app/core/config.py`:
- `CONVERSATION_MAX_HISTORY_MESSAGES`: Maximum number of recent history turns (default: 10).
- `CONVERSATION_MAX_HISTORY_TOKENS`: Maximum token budget allocated to recent history (default: 1500).
- `CONVERSATION_SUMMARY_TRIGGER_MESSAGES`: Message count threshold to trigger rolling summary updates (default: 10).
- `CONVERSATION_SUMMARY_MAX_TOKENS`: Target max token length for rolling summaries (default: 500).

Run full test suite:
```bash
$env:TESTING="True"; .\venv\Scripts\python.exe -m pytest
```

### 5. AI Provider Configuration & Real Local Ollama Setup
The system features a decoupled, provider-agnostic AI architecture for both LLM completion (`AIService`) and vector embeddings (`EmbeddingService`).

**Real Local Ollama Integration**:
1. Install Ollama on your machine (`https://ollama.com`).
2. Pull required models:
   ```bash
   ollama pull qwen3:4b-instruct
   ollama pull embeddinggemma
   ```
3. Configured `.env` settings:
   ```env
   LLM_PROVIDER="ollama"
   LLM_MODEL="qwen3:4b-instruct"
   EMBEDDING_PROVIDER="ollama"
   EMBEDDING_MODEL="embeddinggemma"
   EMBEDDING_DIMENSION=768
   OLLAMA_BASE_URL="http://localhost:11434"
   OLLAMA_EMBEDDING_MODEL="embeddinggemma"
   ```
4. Verify provider health:
   ```bash
   curl http://localhost:8000/api/v1/ai/health
   ```

*Note: If `LLM_PROVIDER=ollama` or `EMBEDDING_PROVIDER=ollama` is configured but Ollama is offline/unreachable, the backend returns a clear `503 Service Unavailable` error (`AIProviderUnavailableError`). It does NOT silently fall back to mock data.*

### 7. Advanced Retrieval & RAG Quality (Phase 8)
Retrieval configuration parameters in `app/core/config.py`:
- `DENSE_TOP_K`: Top K vector candidates from pgvector (default: 20).
- `LEXICAL_TOP_K`: Top K full-text candidates from tsvector (default: 20).
- `RRF_K`: Constant score factor for Reciprocal Rank Fusion ($RRF = \sum \frac{1.0}{K + rank}$) (default: 60).
- `ENABLE_HYBRID_RETRIEVAL`: Enable/disable hybrid dense + lexical retrieval (default: True).
- `ENABLE_RERANKING`: Enable candidate reranking step (default: True).
- `RERANKER_PROVIDER`: Selected reranker implementation (`mock` | `cohere`) (default: `mock`).
- `COHERE_API_KEY`: Cohere API key (gracefully degrades to RRF fused order if missing/unreachable).

Run Phase 8 Automated Retrieval Benchmark:
```bash
$env:TESTING="True"; .\venv\Scripts\python.exe -m pytest tests/test_retrieval_benchmark.py -v
```

### 8. Multimodal PDF Intelligence (Phase 9)
Multimodal PDF configuration parameters in `app/core/config.py`:
- `OCR_PROVIDER`: Selected OCR implementation (`pymupdf` | `tesseract` | `mock`). Default: `pymupdf`.
- `OCR_LANGUAGE`: Target OCR language (default: `eng`).
- `VISION_PROVIDER`: Selected multimodal vision provider (`mock` | `ollama` | `disabled`). Default: `mock`.
- `VISION_MODEL`: Local vision model name (default: `llava`).
- `OLLAMA_VISION_BASE_URL`: Endpoint URL for vision provider (default: `http://localhost:11434`).

Run Phase 9 Multimodal Intelligence Test Suite:
```bash
$env:TESTING="True"; .\venv\Scripts\python.exe -m pytest tests/test_multimodal_intelligence.py -v
```

### 10. Multi-Document Intelligence & Research Workspaces (Phase 12)
Workspace configuration settings in `app/core/config.py`:
- `ENABLE_MULTI_DOC_WORKSPACE`: Enable/disable multi-document workspace features (default: True).
- `MAX_DOCUMENTS_PER_WORKSPACE`: Maximum allowed PDFs per research workspace collection (default: 20).

Run Phase 12 Multi-Document Intelligence Test Suite:
```bash
$env:TESTING="True"; .\venv\Scripts\python.exe -m pytest tests/test_multi_document_intelligence.py -v
```

### 11. Unified AI Evaluation CLI & Quality Engineering (Phase 13)
Run evaluation benchmarks via CLI:
```bash
# List benchmark datasets:
.\venv\Scripts\python.exe -m app.eval list

# Run evaluation benchmark:
.\venv\Scripts\python.exe -m app.eval run --dataset retrieval-v1 --provider ollama --model qwen3:4b-instruct --output console
```

Run Phase 13 Evaluation Test Suite:
```bash
$env:TESTING="True"; .\venv\Scripts\python.exe -m pytest tests/test_evaluation_framework.py -v
```

### 13. Production Containerization & Deployment (Phase 14)
Run production multi-container stack via Docker Compose:
```bash
docker-compose -f docker-compose.prod.yml up --build -d
```
Inspect operational metrics router:
```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/v1/monitoring/health
```
Run Phase 14 Production Hardening Test Suite:
```bash
$env:TESTING="True"; .\venv\Scripts\python.exe -m pytest tests/test_production_hardening.py -v
```

### 14. Frontend Setup
```bash
cd frontend
npm install
npm run dev
npm run build
```

The frontend will be available at `http://localhost:3000` and the API at `http://localhost:8000`.




