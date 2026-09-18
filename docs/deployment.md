# Production Deployment & Infrastructure Guide

## 1. Container Topology

PolicyLens AI deploys as a multi-container Docker application:

```
[Internet]
    |
    v (Port 80)
[policylens_frontend: Nginx 1.27]
    |
    |-- Static Assets (React 19 build)
    |-- Reverse Proxy /api/ --> [policylens_backend: Gunicorn WSGI] (Port 8000)
                                    |
                                    |-- [policylens_postgres: pgvector pg16] (Port 5433:5432)
                                    |-- [policylens_redis: Redis 7-alpine] (Port 6379)
                                    |
                                [policylens_celery_worker: Celery 5.6]
```

---

## 2. Environment Configuration (.env)

```ini
# Django Core
DJANGO_SECRET_KEY=production-crypto-random-key-64-chars
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=policylens.yourdomain.com,localhost,127.0.0.1,backend

# PostgreSQL with pgvector
POSTGRES_DB=policylens_db
POSTGRES_USER=policylens_user
POSTGRES_PASSWORD=strong-production-db-password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_EXTERNAL_PORT=5433

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# AI Provider Integration
LLM_PROVIDER=gemini        # 'gemini' | 'openai' | 'mock'
EMBEDDING_PROVIDER=gemini  # 'gemini' | 'openai' | 'mock'
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Rate Limiting
THROTTLE_UPLOAD_RATE=10/minute
THROTTLE_ANALYSIS_RATE=10/minute
THROTTLE_CHAT_RATE=30/minute
```

---

## 3. Operational Runbook

### Build and Start Containers
```bash
docker compose build
docker compose up -d
```

### Inspect Container Health
```bash
docker compose ps
```

### Run Migrations Inside Production Container
```bash
docker compose exec backend python manage.py migrate
```

### Run Test Suite in Containerized Environment
```bash
docker compose exec backend pytest -v
```

### Inspect Live Worker Logs
```bash
docker compose logs -f celery_worker
```

