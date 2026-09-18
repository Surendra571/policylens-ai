# PolicyLens AI

> **AI-powered insurance policy intelligence.** Upload any insurance PDF — health, motor, life, travel — and instantly get structured clause extraction, grounded Q&A with verified citations, and plain-language explanations.

[![Python](https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5-092e20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20+%20pgvector-336791?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What It Does

Upload an insurance policy PDF. PolicyLens AI will:

- **Extract and categorize every clause** — coverages, exclusions, waiting periods, sub-limits, deductibles, claim requirements, and more
- **Answer policy questions in plain language** via grounded RAG, with exact page-number citations verified against the source document
- **Work with any insurance type** — health, motor, life, term life, travel, home, property, personal accident, and commercial

---

## Architecture

### System Overview

PolicyLens AI is a **modular monolith** — all Django apps share one process and one PostgreSQL database, gaining transactional integrity and simple security, while Celery offloads all heavy AI/ML work asynchronously.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                                    │
│                    http://localhost (port 80)                            │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Nginx 1.27        │  ← Reverse proxy + static files
                    │   (Frontend SPA)    │    React 19 · TypeScript · Vite
                    └──────────┬──────────┘
                               │ /api/v1/* proxied
                    ┌──────────▼──────────────────────┐
                    │   Django REST Framework          │
                    │   (Gunicorn WSGI · port 8000)    │
                    │                                  │
                    │  ┌─────────┐  ┌──────────────┐  │
                    │  │accounts │  │  policies    │  │
                    │  ├─────────┤  ├──────────────┤  │
                    │  │ docs    │  │  clauses     │  │
                    │  ├─────────┤  ├──────────────┤  │
                    │  │  chat   │  │  ai_engine   │  │
                    │  └─────────┘  └──────────────┘  │
                    └──────┬─────────────────┬─────────┘
                           │                 │
          ┌────────────────▼──┐         ┌────▼──────────────────┐
          │ PostgreSQL 16      │         │  Redis 7 (Alpine)      │
          │ + pgvector         │         │  Broker + Cache        │
          │                   │         └────┬──────────────────-┘
          │  • Policy data     │              │ task queue
          │  • Clause store    │         ┌────▼──────────────────┐
          │  • 768-dim vectors │         │  Celery Worker         │
          │  • Cosine search  │         │  (concurrency=4)       │
          │    via <=> op      │         │                        │
          └───────────────────┘         │  • PDF validation      │
                    ▲                   │  • PyMuPDF extraction  │
                    │   writes chunks   │  • Tesseract OCR       │
                    └───────────────────│  • Policy-aware chunk  │
                                        │  • Embedding (768d)    │
                                        │  • LLM extraction      │
                                        │  • Citation verify     │
                                        └────────────────────────┘
```

### Container Map

| Container | Image | Role | Port |
|---|---|---|---|
| `policylens_frontend` | Custom (Nginx + Vite build) | React SPA + reverse proxy | `80` |
| `policylens_backend` | Custom (Python 3.12-slim) | Django API + Gunicorn | `8000` |
| `policylens_celery_worker` | Same as backend | Async AI/ML pipeline | — |
| `policylens_postgres` | `pgvector/pgvector:pg16` | Database + vector store | `5433` (host) |
| `policylens_redis` | `redis:7-alpine` | Task broker + cache | `6379` |

All containers run on the isolated `policylens_net` bridge network.

---

### Django App Responsibilities

| App | Responsibility |
|---|---|
| `accounts` | User registration, PBKDF2 hashing, SimpleJWT token issuance & rotation |
| `policies` | Policy CRUD, status state machine (`PENDING → ANALYZING → COMPLETED`) |
| `documents` | PDF upload, SHA-256 dedup, PyMuPDF text extraction, Tesseract OCR fallback, policy-aware chunking, vector embeddings |
| `clauses` | Stores extracted clauses with category, verbatim source text, page provenance |
| `chat` | RAG Q&A sessions, message history, citation-verified responses |
| `ai_engine` | LLM abstraction (Gemini / OpenAI / Mock), heuristic parser, structured extraction, `CitationVerifier` |
| `core` | Health check, custom exception handler, IDOR-safe `IsOwner` permission |

---

### Document Intelligence Pipeline

Every uploaded PDF goes through this 10-step pipeline entirely in the background (Celery worker):

```
 1. Upload & Validate
    └─ MIME check · magic bytes (%PDF-) · size ≤ 25 MB · SHA-256 dedup

 2. Text Extraction
    └─ PyMuPDF page-by-page → if page < 40 chars → Tesseract OCR fallback

 3. Policy-Aware Chunking
    └─ Preserves clause headings, numbered lists, section boundaries
       Never splits mid-clause or mid-sentence

 4. Vector Embedding  (768 dimensions)
    └─ Batched embedding generation → stored in DocumentChunk.embedding

 5. Structured LLM Extraction
    └─ Windowed batch extraction over chunks
       → Coverages, Exclusions, Waiting Periods, Deductibles,
         Limits, Conditions, Claims, Eligibility, Renewal, Cancellation

 6. Heuristic Fallback
    └─ If LLM returns 0 items → rule-based SECTION_ROUTING parser
       handles any insurance domain without hard-coded field names

 7. Citation Verification
    └─ Every extracted clause.source_text is grounded-checked
       against actual chunk content — rejects any hallucinated citations

 8. Atomic DB Write
    └─ transaction.atomic() → Policy + Clause bulk_create in one commit

 9. Policy Status → COMPLETED
    └─ Frontend polling detects completion, renders results

10. RAG Q&A (on-demand)
    └─ Question → embed → pgvector CosineDistance (<=>)
       → top-k chunks → LLM with strict context → CitationVerifier → response
```

---

### RAG & Anti-Hallucination Design

```
User Question
     │
     ▼
Embed question (768d)
     │
     ▼
PostgreSQL pgvector cosine search  ← scoped to user's policy only
     │                               (prevents cross-tenant data leak)
     ▼
Top-k most relevant chunks
     │
     ▼
Inject into strict system prompt
     │
     ▼
LLM generates answer + citations
     │
     ▼
CitationVerifier
  • Checks every cited page number exists in DocumentChunk table
  • Checks cited text appears verbatim in the chunk
  • Rejects any citation not grounded in the database
     │
     ▼
Verified response → user
```

---

### Why Modular Monolith (Not Microservices)

| Concern | Decision |
|---|---|
| **Transactional integrity** | `transaction.atomic()` across policy + clause writes — impossible to split across services without distributed transactions |
| **Security** | JWT is validated once at the perimeter; row-level `IsOwner` checks via Django ORM. No inter-service identity propagation needed |
| **Latency** | In-process app calls have zero network overhead. The only async boundary is CPU-heavy OCR / LLM work — handled by Celery |
| **Deployability** | Single `docker compose up` command. No service mesh, no service discovery, no distributed tracing setup required |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | Python 3.12, Django 5, Django REST Framework, SimpleJWT, Gunicorn |
| **Database** | PostgreSQL 16 + `pgvector` (cosine similarity search) |
| **Task Queue** | Celery 5 + Redis 7 (async document processing & AI pipeline) |
| **AI / NLP** | Google Gemini / OpenAI / Mock provider, PyMuPDF, Tesseract OCR, Pydantic v2 |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, TanStack Query |
| **Infrastructure** | Docker, Docker Compose, Nginx, GitHub Actions CI/CD |

---

## Project Structure

```
policylens-ai/
├── backend/                  # Django API
│   ├── apps/
│   │   ├── accounts/         # JWT auth (register, login, refresh)
│   │   ├── policies/         # Policy CRUD + analysis endpoints
│   │   ├── documents/        # PDF upload, OCR, chunking, embeddings
│   │   ├── clauses/          # Extracted clause models
│   │   ├── chat/             # RAG Q&A with citation verification
│   │   ├── ai_engine/        # LLM abstraction, extraction, heuristic parser
│   │   └── core/             # Health check, permissions, exception handler
│   ├── config/               # Django settings, URLs, WSGI/ASGI
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/                 # React + TypeScript SPA
│   ├── src/
│   │   ├── components/       # UploadPolicy, PolicyOverview, Chat, Sidebar…
│   │   ├── services/         # Axios API client
│   │   └── types.ts
│   └── package.json
├── docs/                     # Deep-dive engineering docs
├── .env.example              # Environment variable template
├── docker-compose.yml        # Development stack
├── docker-compose.prod.yml   # Production stack
└── README.md
```

---

## Quick Start (Docker — Recommended)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Surendra571/policylens-ai.git
cd policylens-ai
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set the required values:

```env
# Required: generate a strong secret key
DJANGO_SECRET_KEY=your-very-long-random-secret-key-here

# Required for AI extraction — choose one provider
LLM_PROVIDER=gemini          # Options: mock | gemini | openai | anthropic
GEMINI_API_KEY=your-gemini-api-key-here
# OPENAI_API_KEY=your-openai-api-key-here

# Database (defaults work out of the box with Docker)
POSTGRES_PASSWORD=a-secure-db-password
```

> **No API key?** Set `LLM_PROVIDER=mock` to run with a deterministic mock provider — all features work, but AI extraction returns placeholder data.

### 3. Build and start all containers

```bash
docker compose build
docker compose up -d
```

### 4. Verify everything is running

```bash
docker compose ps
```

All containers should show `healthy`. Then open:

| URL | Description |
|---|---|
| `http://localhost` | Main application |
| `http://localhost:8000/api/v1/health/` | Health check (all services) |
| `http://localhost:8000/api/schema/swagger-ui/` | Interactive API docs |

---

## Local Development (Without Docker)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start just postgres + redis via Docker, then run locally:
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

### Start only infrastructure containers

```bash
docker compose up -d postgres redis
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | ✅ | — | Django secret key (50+ random chars) |
| `DJANGO_DEBUG` | | `False` | Enable Django debug mode |
| `DJANGO_ALLOWED_HOSTS` | | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `POSTGRES_DB` | | `policylens_db` | Database name |
| `POSTGRES_USER` | | `policylens_user` | Database user |
| `POSTGRES_PASSWORD` | ✅ | — | Database password |
| `POSTGRES_HOST` | | `postgres` | Host (`localhost` for local dev, `postgres` for Docker) |
| `POSTGRES_PORT` | | `5432` | Database port |
| `REDIS_URL` | | `redis://redis:6379/0` | Redis connection URL |
| `LLM_PROVIDER` | | `mock` | AI provider: `mock` \| `gemini` \| `openai` \| `anthropic` |
| `GEMINI_API_KEY` | | — | Google Gemini API key |
| `OPENAI_API_KEY` | | — | OpenAI API key |
| `EMBEDDING_MODEL` | | `text-embedding-3-small` | Embedding model name |
| `MAX_UPLOAD_SIZE_MB` | | `25` | Max PDF upload size in MB |

---

## Running Tests

```bash
# Run full test suite inside the running Docker container
docker compose exec backend pytest -v

# Run with coverage report
docker compose exec backend pytest -v --cov=apps --cov-report=term-missing

# Run a specific test module
docker compose exec backend pytest apps/policies/test_sample_policy_regression.py -v

# Run tests locally (requires local backend setup)
cd backend && pytest -v
```

---

## API Overview

All endpoints are prefixed with `/api/v1/`.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register/` | Create account |
| `POST` | `/auth/login/` | Get JWT tokens |
| `POST` | `/auth/refresh/` | Refresh access token |
| `GET` | `/auth/me/` | Current user profile |

### Policies

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/policies/` | List user's policies |
| `POST` | `/policies/` | Create a new policy |
| `GET` | `/policies/{id}/` | Get policy details |
| `DELETE` | `/policies/{id}/` | Delete policy |
| `POST` | `/policies/{id}/documents/` | Upload PDF document |
| `POST` | `/policies/{id}/analyze/` | Trigger AI analysis |
| `GET` | `/policies/{id}/analysis/` | Poll analysis results |
| `POST` | `/policies/{id}/chat/` | Ask a question about the policy |

Full request/response schemas: [`docs/api.md`](docs/api.md)

---

## After Code Changes

When you modify backend Python files, rebuild and restart:

```bash
docker compose build backend celery_worker
docker compose up -d backend celery_worker
```

When you modify frontend files:

```bash
docker compose build frontend
docker compose up -d frontend
```

---

## Documentation

| Document | Description |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Detailed system architecture and component diagram |
| [`docs/ai-pipeline.md`](docs/ai-pipeline.md) | RAG pipeline, chunking strategy, citation verification |
| [`docs/database.md`](docs/database.md) | Schema design, pgvector queries, ER diagram |
| [`docs/security.md`](docs/security.md) | JWT lifecycle, IDOR prevention, upload security |
| [`docs/api.md`](docs/api.md) | Complete REST API reference |
| [`docs/deployment.md`](docs/deployment.md) | Production deployment guide |
| [`docs/interview-guide.md`](docs/interview-guide.md) | Engineering design decisions Q&A |

---

## Troubleshooting

**Containers not starting?**
```bash
docker compose logs backend
docker compose logs celery_worker
```

**Database connection errors?**  
Make sure `POSTGRES_HOST=postgres` in `.env` (not `localhost`) when running inside Docker.

**Analysis shows 0 clauses?**  
Check that `LLM_PROVIDER` and the corresponding API key are set correctly in `.env`, then rebuild:
```bash
docker compose build backend celery_worker && docker compose up -d backend celery_worker
```

**Policy type 400 error after updating models?**  
The backend code is baked into the Docker image — always rebuild after model changes:
```bash
docker compose build backend celery_worker && docker compose up -d backend celery_worker
```

---

## License

MIT — see [LICENSE](LICENSE).
