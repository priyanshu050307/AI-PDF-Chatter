# AI PDF Chatter — Production Runbook & Operations Guide

## 1. Production Architecture Overview
AI PDF Chatter is deployed as a containerized multi-service SaaS architecture behind an Nginx reverse proxy.

```text
Public Internet (Ports 80 / 443)
       │
       ▼
 ┌──────────┐
 │  Nginx   │ (TLS Termination, Security Headers, Rate Limiting, Ollama Port 11434 Protection)
 └────┬─────┘
      │
      ├────────────────────────────┐
      ▼                            ▼
┌───────────┐                ┌───────────┐
│ Next.js   │ (Port 3000)    │ FastAPI   │ (Port 8000)
└───────────┘                └─────┬─────┘
                                   │
      ┌──────────────┬─────────────┼──────────────┬──────────────┐
      ▼              ▼             ▼              ▼              ▼
 ┌──────────┐   ┌──────────┐  ┌──────────┐   ┌──────────┐   ┌──────────┐
 │PostgreSQL│   │  Redis   │  │ MinIO/S3 │   │ Celery   │   │ Ollama   │ (Private Net Only)
 │+pgvector │   │ (Cache)  │  │(Storage) │   │ Worker   │   │  (LLM)   │
 └──────────┘   └──────────┘  └──────────┘   └──────────┘   └──────────┘
```

---

## 2. Deployment Procedures

### Initial Production Start
```bash
# 1. Clone production repository and configure environment variables
cp .env.example .env

# Edit .env with production passwords, JWT_SECRET, and database credentials
nano .env

# 2. Build and launch multi-container production stack
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Verify health probes
curl http://localhost/api/v1/health/readiness
```

### Zero-Downtime Migration Deployment Strategy
1. **Pre-Deployment DB Backup**:
   ```bash
   docker exec -t pdfchatter_postgres_prod pg_dump -U pdfuser pdfchatter > backup_pre_deploy.sql
   ```
2. **Apply Alembic Database Migrations**:
   ```bash
   docker exec -t pdfchatter_backend python -m alembic upgrade head
   ```
3. **Rolling Container Restart**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend worker frontend
   ```

---

## 3. Disaster Recovery & Backup Drills

### Database Backup & Restore Drill
- **Backup**:
  ```bash
  docker exec -t pdfchatter_postgres_prod pg_dump -U pdfuser pdfchatter | gzip > /backups/db_$(date +%Y%m%d_%H%M%S).sql.gz
  ```
- **Restore Drill**:
  ```bash
  gunzip -c /backups/db_20260907_210000.sql.gz | docker exec -i pdfchatter_postgres_prod psql -U pdfuser -d pdfchatter
  ```

### Object Storage Backup Drill
- **Backup**: Sync MinIO/S3 data directory `/data` to offsite encrypted storage.
- **Restore**: Restore object data directory and restart `pdfchatter_minio_prod`.

---

## 4. Incident Response & Troubleshooting Runbooks

### Incident A: High 5xx HTTP Error Rate
1. Check Nginx logs:
   ```bash
   docker logs --tail 100 pdfchatter_nginx
   ```
2. Check FastAPI backend logs (filter by `X-Correlation-ID`):
   ```bash
   docker logs --tail 100 pdfchatter_backend
   ```
3. Check PostgreSQL connection pool:
   ```bash
   curl -H "Authorization: Bearer <TOKEN>" http://localhost/api/v1/monitoring/health
   ```

### Incident B: Background Celery Worker Backlog / Worker Failure
1. Check Celery worker logs:
   ```bash
   docker logs --tail 100 pdfchatter_worker
   ```
2. Scale worker concurrency:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --scale worker=3
   ```

### Incident C: Ollama Local AI Unreachable / Degradation
1. Check AI health endpoint:
   ```bash
   curl http://localhost/api/v1/ai/health
   ```
2. Verify Ollama process on host:
   ```bash
   curl http://localhost:11434/api/tags
   ```
3. *Note: System gracefully degrades non-AI features (reading, highlights, basic search) when Ollama is offline.*
