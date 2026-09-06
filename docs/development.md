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

### 6. Advanced Retrieval & RAG Quality (Phase 8)
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

### 7. Frontend Setup
```bash
cd frontend
npm install
npm run dev
npm run build
```

The frontend will be available at `http://localhost:3000` and the API at `http://localhost:8000`.


