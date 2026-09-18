# PolicyLens AI

> **Production-Grade Insurance Policy Intelligence & Grounded Conversational RAG Platform.**  
> Ingest complex insurance contracts (health, motor, life, travel, commercial), extract structured clauses across 10+ standardized categories, and enable anti-hallucinatory Q&A with physical page citations verified directly against PostgreSQL storage.

---

[![CI Build](https://github.com/Surendra571/policylens-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Surendra571/policylens-ai/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Django 5.2](https://img.shields.io/badge/Django-5.2-092e20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF 3.15+](https://img.shields.io/badge/DRF-3.15+-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.2.5-blue.svg)](https://github.com/pgvector/pgvector)
[![Celery 5.3+](https://img.shields.io/badge/Celery-5.3+-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis 7](https://img.shields.io/badge/Redis-7-dc382d?logo=redis&logoColor=white)](https://redis.io/)
[![React 19](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript 5](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6-646cff?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-38bdf8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Tests Passing](https://img.shields.io/badge/Tests-102%20Passed-brightgreen.svg)](#18-testing--quality-assurance)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Problem in Insurance Documents](#2-the-problem-in-insurance-documents)
3. [The Solution: PolicyLens AI](#3-the-solution-policylens-ai)
4. [Key Features](#4-key-features)
5. [End-to-End Product Flow](#5-end-to-end-product-flow)
6. [Architecture & System Design](#6-architecture--system-design)
7. [AI & Grounded RAG Pipeline Deep Dive](#7-ai--grounded-rag-pipeline-deep-dive)
8. [Document Processing Pipeline](#8-document-processing-pipeline)
9. [Evidence & Citation Verification Engine](#9-evidence--citation-verification-engine)
10. [Technology Stack](#10-technology-stack)
11. [Repository & Directory Structure](#11-repository--directory-structure)
12. [Database Design & Data Models](#12-database-design--data-models)
13. [API Reference & Endpoints](#13-api-reference--endpoints)
14. [Asynchronous Processing & Celery Tasks](#14-asynchronous-processing--celery-tasks)
15. [Security & Multi-Tenancy Architecture](#15-security--multi-tenancy-architecture)
16. [Reliability, Resilience & Edge Cases](#16-reliability-resilience--edge-cases)
17. [Testing & Quality Assurance](#17-testing--quality-assurance)
18. [Local Development Setup (Without Docker)](#18-local-development-setup-without-docker)
19. [Environment Variables Reference](#19-environment-variables-reference)
20. [Docker & Containerized Setup](#20-docker--containerized-setup)
21. [Production Deployment Guide](#21-production-deployment-guide)
22. [Configuration & Model Switching](#22-configuration--model-switching)
23. [UI Tour & Component Walkthrough](#23-ui-tour--component-walkthrough)
24. [Engineering Decisions & Architecture Trade-Offs](#24-engineering-decisions--architecture-trade-offs)
25. [Current Limitations & Known Constraints](#25-current-limitations--known-constraints)
26. [Roadmap & Future Scope](#26-roadmap--future-scope)
27. [Real-World Use Cases & Sample Scenarios](#27-real-world-use-cases--sample-scenarios)
28. [Troubleshooting & FAQ](#28-troubleshooting--faq)
29. [Contributing](#29-contributing)
30. [License](#30-license)

---

## 1. Project Overview

**PolicyLens AI** is an open-source, full-stack InsurTech platform engineered to ingest, parse, structure, and query complex insurance policy contracts.

Insurance policies are legal agreements that often exceed 50 to 100 pages, filled with specialized terminology, conditional coverage schedules, waiting period matrices, copays, and exclusions. For policyholders, claim adjusters, and financial advisors, answering basic questions like *"Is robotic knee surgery covered after 2 years?"* or *"What is my accidental deductible?"* usually requires hours of manual cross-referencing.

PolicyLens AI solves this by coupling:
- **Fast text extraction and OCR fallback** (PyMuPDF + Tesseract)
- **Domain-aware policy chunking** preserving hierarchical legal headings
- **Native vector similarity search** using PostgreSQL with `pgvector`
- **Dual extraction pipeline** (Structured LLM extraction + universal regex heuristic fallback)
- **Strict, cryptographic anti-hallucination verification** (`CitationVerifier`) that guarantees every cited claim and page number exists verbatim in the database
- **A reactive, modern single-page frontend** built on React 19, TypeScript, and Tailwind CSS

---

## 2. The Problem in Insurance Documents

Insurance contracts present severe technical challenges for automated systems and human readers alike:

- **Labyrinthine Structure:** Exclusions often override coverages stated 30 pages earlier. Standard RAG architectures that chunk blindly by fixed token sizes break clauses in half, separating conditions from their qualifying sub-clauses.
- **Scanned and Low-Quality Artifacts:** Many policies in circulation are rasterized PDF scans with zero selectable text layers or noisy OCR artifacts.
- **The Catastrophic Cost of Hallucinations:** In healthcare and insurance, a hallucinated answer ("Yes, knee surgery is 100% covered without waiting periods") can lead to major unexpected out-of-pocket financial liability or denied claims. Generative models cannot be trusted without strict database-level citation verification.
- **Data Privacy & Tenancy:** Insurance documents contain confidential personal and financial data. Multi-tenant systems must guarantee strict row-level isolation and sanitize sensitive logs.

---

## 3. The Solution: PolicyLens AI

PolicyLens AI addresses these challenges with an enterprise-grade, deterministic architecture:

1. **Deterministic Ingestion & Deduplication:** Validates PDF magic bytes (`%PDF-`), calculates SHA-256 fingerprints to prevent duplicate storage, and extracts native text layers with high-performance C bindings (`fitz`).
2. **Intelligent OCR Routing:** Pages with fewer than 40 extracted characters automatically fall back to Tesseract OCR at 300 DPI, recovering scanned pages transparently.
3. **Policy-Aware Semantic Chunking:** Chunks text along legal clause headers (`Section`, `Exclusion`, `Coverage`, `Clause`, roman numerals, bulleted schedules) rather than arbitrary byte boundaries.
4. **PostgreSQL pgvector Store:** Embeds chunks into 768-dimensional vectors stored in the primary relational database, eliminating the network latency, synchronization drift, and operational complexity of separate third-party vector databases.
5. **Strict Citation Engine:** When an LLM generates a response or extracts clauses, the `CitationVerifier` validates that every cited page number and snippet actually matches the physical chunks stored for that specific user policy. Non-matching citations are rejected.
6. **Universal Heuristic Fallback:** If an LLM provider experiences outages, quota exhaustion, or returns 0 structured clauses, the system falls back to the `HeuristicPolicyParser` across 19 standard insurance domains.

---

## 4. Key Features

- **Multi-Format PDF Ingestion:** Upload policies up to 25 MB with MIME type verification, magic byte enforcement, and SHA-256 duplicate detection.
- **Hybrid OCR Engine:** Seamlessly transitions between PyMuPDF native text extraction and Tesseract OCR for image-only or scanned policy pages.
- **10+ Standardized Clause Categories:** Automatically detects and categorizes clauses into:
  - `COVERAGE` — In-scope protections and benefits
  - `EXCLUSION` — Explicitly uncovered conditions and perils
  - `WAITING_PERIOD` — Initial, specific, or pre-existing disease delay schedules
  - `DEDUCTIBLE` — Compulsory and voluntary out-of-pocket thresholds
  - `LIMIT` — Annual maximum sums insured and sub-limits (room rent, ICU, etc.)
  - `CONDITION` — Policyholder obligations and warranty requirements
  - `CLAIM_REQUIREMENT` — Notice timelines, cashless protocols, and document checklists
  - `ELIGIBILITY` — Age criteria, pre-medical checkup requirements, and family definitions
  - `RENEWAL` — Grace periods, portability rights, and cumulative bonus rules
  - `CANCELLATION` — Free-look periods, premium refund tables, and termination clauses
- **Dual-Path Extraction:** Primary LLM extraction (Google Gemini / OpenAI / Anthropic / Mock) backed by a 19-domain rule-based heuristic parser.
- **PostgreSQL Native Vector Search:** Cosine similarity retrieval (`<=>` operator) executed directly in PostgreSQL via `pgvector` with strict multi-tenant filtering by `policy_id`.
- **Database-Grounded RAG Chat:** Conversational assistant that answers questions using only retrieved chunks, returning exact page numbers and clickable citations.
- **Interactive Source Viewer:** Click any cited page badge in the UI to open the `SourceViewerModal`, rendering the exact source snippet directly from database records.
- **Asynchronous Architecture:** Celery 5 worker pool backed by Redis 7 handles compute-intensive parsing and embedding without blocking web workers.
- **Zero-Trust Multi-Tenancy:** JWT authentication (stateless access + rotating refresh tokens), IDOR-safe row-level ownership validation (`IsOwner`), and privacy-safe logging that strips PII.

---

## 5. End-to-End Product Flow

```
[User Browser / SPA]
       │
       │  1. POST /api/v1/policies/ (Create policy metadata)
       │  2. POST /api/v1/policies/{id}/documents/ (Upload PDF binary)
       ▼
[Nginx Reverse Proxy :80]
       │
       │  3. Route /api/* to Django Backend
       ▼
[Django REST Framework :8000]
       │
       │  4. Validate magic bytes (%PDF-), compute SHA-256, save file
       │  5. Dispatch asynchronous processing job to Celery
       ▼
[Redis 7 Broker :6379]
       │
       │  6. Celery Worker picks up task
       ▼
[Celery Worker Cluster]
       │
       ├──> Step A: Extract text page-by-page (PyMuPDF)
       │            └─ If text < 40 chars -> Trigger Tesseract OCR
       │
       ├──> Step B: Execute PolicyAwareChunker
       │            └─ Chunk along legal boundaries, retain page ranges
       │
       ├──> Step C: Generate 768d Vector Embeddings
       │            └─ Bulk write to DocumentChunk table (pgvector)
       │
       ├──> Step D: Structured LLM Clause Extraction
       │            └─ If LLM empty -> Trigger HeuristicPolicyParser fallback
       │
       ├──> Step E: CitationVerifier
       │            └─ Validate extracted clauses against stored chunk content
       │
       └──> Step F: Atomic Persistence (transaction.atomic)
                    └─ Bulk insert verified clauses, mark Policy COMPLETED
       │
       ▼
[PostgreSQL 16 + pgvector :5432]
       │
       │  7. Frontend polls GET /api/v1/policies/{id}/analysis/
       ▼
[React 19 Frontend Dashboard]
       │
       │  8. User explores categorized clauses & asks question
       │  9. POST /api/v1/policies/{id}/chat/
       ▼
[Grounded RAG Execution]
       │
       ├──> Vectorize user query (768d)
       ├──> Query pgvector cosine distance (<=>) scoped to policy_id
       ├──> Assemble strict context prompt
       ├──> Query LLM -> Synthesize answer with [Page X] tags
       ├──> Run CitationVerifier against DB chunks
       └──> Return verified response + page citations to user
```

---

## 6. Architecture & System Design

### 6.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT WEB BROWSER                             │
│                  http://localhost:80 (Production Port)                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP / HTTPS
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         NGINX REVERSE PROXY                             │
│                  • Static File Serving (React SPA)                      │
│                  • Client Request Proxying (/api/v1/*)                  │
│                  • Upload Buffer Configuration (25MB)                   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼ /api/v1/*                             ▼ Static assets
┌──────────────────────────────────────┐     ┌────────────────────────────┐
│         DJANGO REST FRAMEWORK        │     │ React 19 Frontend (SPA)    │
│            (Gunicorn WSGI)           │     │ • TypeScript / Vite        │
│                                      │     │ • Tailwind CSS             │
│  ┌────────────────────────────────┐  │     │ • TanStack Query           │
│  │ apps.accounts (JWT Auth)       │  │     │ • Lucide React             │
│  ├────────────────────────────────┤  │     └────────────────────────────┘
│  │ apps.policies (Policy CRUD)    │  │
│  ├────────────────────────────────┤  │
│  │ apps.documents (Upload & Text) │  │
│  ├────────────────────────────────┤  │
│  │ apps.clauses (Clause Store)    │  │
│  ├────────────────────────────────┤  │
│  │ apps.chat (RAG Sessions)       │  │
│  ├────────────────────────────────┤  │
│  │ apps.ai_engine (LLM & Verify)  │  │
│  ├────────────────────────────────┤  │
│  │ apps.core (Health & Exceptions)│  │
│  └────────────────────────────────┘  │
└──────────────┬────────────────┬──────┘
               │                │
               │ Writes tasks   │ Reads/writes data
               ▼                ▼
┌────────────────────────┐   ┌───────────────────────────────────────────┐
│     REDIS 7 BROKER     │   │      POSTGRESQL 16 + PGVECTOR STORE       │
│  • Celery Task Queue   │   │                                           │
│  • Distributed Cache   │   │  • User, Policy, Document records         │
│                        │   │  • DocumentPage (cleaned text / OCR flag) │
│                        │   │  • DocumentChunk (768-dim vector index)   │
│                        │   │  • Clause store (10+ categories)          │
│                        │   │  • Conversation & Message history         │
│                        │   │  • Cosine distance search (<=> operator)  │
└──────────────┬─────────┘   └─────────────────────▲─────────────────────┘
               │                                   │
               │ Pops background tasks             │ Writes chunks & clauses
               ▼                                   │
┌──────────────────────────────────────────────────┴─────────────────────┐
│                       CELERY WORKER CLUSTER                            │
│                         (Concurrency: 4)                               │
│                                                                        │
│  • PDF Validation & SHA-256 Check                                      │
│  • PyMuPDF Native Text Layer Extraction                                │
│  • Tesseract OCR Fallback (<40 chars/page)                             │
│  • PolicyAwareChunker (Semantic clause & heading boundaries)           │
│  • Vector Embedding Generation (768 dimensions)                        │
│  • Structured LLM Extraction (Gemini / OpenAI / Anthropic / Mock)      │
│  • Universal Heuristic Fallback Parser (19 insurance domains)          │
│  • CitationVerifier (Strict DB grounding against physical text)        │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Container Map

| Service Name | Docker Image | Role in System | Internal Port | Host Port | Healthcheck Mechanism |
|---|---|---|---|---|---|
| `policylens_frontend` | Custom (`frontend/Dockerfile`) | React SPA + Nginx reverse proxy | `80` | `80` | `wget -q --spider http://127.0.0.1/healthz` |
| `policylens_backend` | Custom (`backend/Dockerfile`) | Django REST Framework + Gunicorn WSGI | `8000` | `8000` | `curl -f http://localhost:8000/api/v1/health/` |
| `policylens_celery_worker` | Custom (`backend/Dockerfile`) | Celery worker (4 concurrent processes) | — | — | `python -c "from config.celery import app; app.control.ping()"` |
| `policylens_postgres` | `pgvector/pgvector:pg16` | Relational database + vector search | `5432` | `5433` | `pg_isready -U policylens_user -d policylens_db` |
| `policylens_redis` | `redis:7-alpine` | Distributed task broker and cache | `6379` | `6379` | `redis-cli ping` |

All services run inside an isolated Docker bridge network: `policylens_net`.

### 6.3 Django Application Responsibilities

The codebase follows a modular monolith design where domain boundaries are strictly respected:

```
backend/apps/
├── accounts/    # User authentication, PBKDF2 hashing, SimpleJWT issuance/rotation
├── policies/    # Policy lifecycle, status state machine, metadata management
├── documents/   # PDF upload validation, SHA-256 dedup, PyMuPDF, OCR, chunking, embeddings
├── clauses/     # Standardized clause storage, category mapping, page provenance
├── chat/        # Conversational RAG sessions, chat history, citation-verified replies
├── ai_engine/   # Provider abstraction, vector search, prompt construction, CitationVerifier, HeuristicPolicyParser
└── core/        # Centralized healthcheck, custom DRF exception handler, IsOwner permission
```

### 6.4 Why a Modular Monolith?

Instead of adopting distributed microservices prematurely, PolicyLens AI is intentionally structured as a modular monolith:

1. **Transactional Atomicity (`transaction.atomic()`):** Policy creation, document chunking, and clause persistence are coordinated within database transactions. In a microservices architecture, this requires complex two-phase commits (2PC) or distributed saga patterns.
2. **Zero Inter-Service Network Latency:** In-process communication between domain apps incurs zero serialization overhead and zero HTTP/gRPC latency.
3. **Unified Security Model:** JWT verification occurs once at the API perimeter. Domain apps enforce tenant boundaries using standard Django ORM queries (`policy.user == request.user`), eliminating token forwarder proxies or distributed identity synchronization.
4. **Single-Command Developer Experience:** The entire stack builds and deploys cleanly with one `docker compose up` command.

---

## 7. AI & Grounded RAG Pipeline Deep Dive

Standard RAG architectures frequently hallucinate citations, invent page numbers, or quote provisions out of context. PolicyLens AI implements a multi-stage, grounded RAG architecture designed specifically for legal and insurance documents:

```
                       [User Policy Question]
                                 │
                                 ▼
                     [768-Dim Vector Embedding]
                                 │
                                 ▼
             [PostgreSQL pgvector Cosine Search (<=>)]
             • WHERE document_id IN (user_policy_documents)
             • ORDER BY embedding <=> query_vector
             • LIMIT top_k (default: 5)
                                 │
                                 ▼
                    [Evidence Sufficiency Gate]
                     • Minimum similarity score check
                     • Prevents answering ungrounded queries
                                 │
                                 ▼
                     [Strict LLM System Prompt]
                     • Enforces answering ONLY from context
                     • Requires inline [Page X] tags
                     • Explicitly forbids extrapolation
                                 │
                                 ▼
                     [LLM Answer Synthesis]
                                 │
                                 ▼
                    [CitationVerifier Validation]
     ┌───────────────────────────┴───────────────────────────┐
     │ 1. Regex extracts all cited [Page X] tags             │
     │ 2. Queries DocumentChunk table for cited pages        │
     │ 3. Verifies quoted text exists verbatim in chunk      │
     │ 4. Rejects or strips hallucinated citations           │
     └───────────────────────────┬───────────────────────────┘
                                 │
                                 ▼
             [Verified Response + Validated Citations]
```

### 7.1 PostgreSQL pgvector Retrieval

Chunks are retrieved using native SQL cosine distance queries scoped strictly to the authenticated user's policy:

```sql
SELECT id, content, page_start, page_end,
       (embedding <=> %(query_embedding)s) AS distance
FROM documents_documentchunk
WHERE document_id = %(document_id)s
ORDER BY distance ASC
LIMIT %(top_k)s;
```

By filtering on `document_id`, cross-tenant data leakage is mathematically impossible at the query execution level.

### 7.2 Strict Prompt Engineering

The system prompt enforces deterministic citations:
- The LLM is instructed: *"You are an expert insurance policy assistant. Answer the user's question using ONLY the provided policy context. If the answer cannot be found in the context, clearly state that the policy document does not contain this information. For every factual statement, cite the exact source page in the format [Page X]. Never fabricate clauses or page numbers."*

---

## 8. Document Processing Pipeline

The document pipeline transforms raw PDF binaries into searchable, embedded chunks through five sequential phases:

```
[Raw Uploaded PDF]
       │
       ▼
Phase 1: Binary Validation
       • Verify file extension is .pdf
       • Validate magic bytes: file.read(4) == b'%PDF'
       • Enforce file size limit: <= 25 MB
       • Calculate SHA-256 checksum -> prevent duplicate reprocessing
       │
       ▼
Phase 2: Page-by-Page Text Extraction
       • PyMuPDF (fitz) stream parsing with layout awareness
       • Evaluate extracted string length per page:
         - If len(text.strip()) >= 40 chars -> Accept native text layer
         - If len(text.strip()) < 40 chars -> Route page to Tesseract OCR
       │
       ▼
Phase 3: Tesseract OCR Fallback
       • Rasterize PDF page to 300 DPI image pixmap
       • Execute pytesseract.image_to_string()
       • Tag page record with has_ocr=True for auditability
       │
       ▼
Phase 4: PolicyAwareChunker Execution
       • Detects legal section headings via regex:
         (Section\s+\d+|Exclusion\s+\d+|Coverage\s+[A-Z]|Clause\s+\d+|Schedule\s+\w+)
       • Splits text respecting clause boundaries, headings, and bullet points
       • Preserves page_start and page_end on every chunk
       • Enforces target chunk size (~500 words) with 50-word context overlap
       │
       ▼
Phase 5: Embedding & Vector Ingestion
       • Generates 768-dimensional float vectors
       • Bulk-inserts DocumentChunk instances into PostgreSQL
```

---

## 9. Evidence & Citation Verification Engine

The `CitationVerifier` (`apps/ai_engine/citation_verifier.py`) is the core anti-hallucination guardrail of PolicyLens AI. It operates as an automated validation barrier between the LLM and the client:

1. **Extraction:** Scans the generated text for citation markers using regular expressions matching `[Page X]` or `(Page X)`.
2. **Page Range Validation:** Verifies that the cited page number $X$ is within the valid range ($1 \le X \le \text{page\_count}$) of the target document.
3. **Database Grounding:** Queries the `DocumentChunk` table for chunks covering page $X$ belonging to that specific document.
4. **Verbatim Text Check:** Compares the cited sentence or clause quote against the physical text stored in the chunk. If the LLM fabricated an exclusion or modified critical terms (e.g. changing *"30 days"* to *"60 days"*), the citation fails verification.
5. **Rejection & Filtering:** Unverified citations are stripped from the response, and ungrounded claims are flagged, ensuring that users are never presented with fabricated legal terms.

---

## 10. Technology Stack

### Backend Infrastructure
| Component | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | `3.12` | Core backend runtime |
| Web Framework | Django | `5.2` (Django 5.x) | Web framework and ORM |
| API Framework | Django REST Framework | `3.15+` | REST API serialization and views |
| Authentication | djangorestframework-simplejwt | `5.3+` | Stateless JWT token issuance and rotation |
| Database Engine | PostgreSQL | `16` | Primary ACID relational database |
| Vector Extension | pgvector | `0.2.5` | 768-dimensional cosine vector indexing |
| Async Worker | Celery | `5.3+` | Distributed task execution for OCR and AI |
| Message Broker | Redis | `7-alpine` | Celery task queue and cache backend |
| PDF Engine | PyMuPDF (`fitz`) | `1.23+` | High-speed native PDF parsing |
| OCR Engine | Tesseract OCR (`pytesseract`) | `5.x` | Fallback OCR for scanned policies |
| Schema Validation | Pydantic | `v2.6+` | Structured LLM output parsing |
| API Documentation | drf-spectacular | `0.27+` | OpenAPI 3.0 schema and Swagger/Redoc UI |
| WSGI Server | Gunicorn | `21.2+` | Production HTTP application server |
| Linter & Formatter | Ruff | `0.16.8` | High-performance Python linter |
| Test Runner | Pytest / Pytest-Django | `8.x` | Automated test suite execution |

### Frontend Infrastructure
| Component | Technology | Version | Purpose |
|---|---|---|---|
| UI Framework | React | `19.0+` | Component-based user interface |
| Language | TypeScript | `5.6+` | Type-safe client-side application logic |
| Build Tool | Vite | `6.0+` | Development server and production bundling |
| Styling | Tailwind CSS | `3.4+` | Utility-first responsive design |
| State & Cache | TanStack Query (`@tanstack/react-query`) | `5.x` | Server state management and polling |
| HTTP Client | Axios | `1.7+` | Promise-based API request client |
| Icons | Lucide React | `0.400+` | Accessible, clean UI iconography |
| Web Server | Nginx | `1.27-alpine` | Production static host & reverse proxy |

---

## 11. Repository & Directory Structure

```
policylens-ai/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI pipeline (Ruff, Pytest, Frontend)
├── backend/
│   ├── apps/
│   │   ├── accounts/            # User authentication & JWT
│   │   │   ├── models.py        # Custom User model (email as username)
│   │   │   ├── serializers.py   # User & Token serializers
│   │   │   ├── urls.py          # /api/v1/auth/ routes
│   │   │   ├── views.py         # Login, Register, Me views
│   │   │   └── test_auth.py     # Auth test suite
│   │   ├── ai_engine/           # Core intelligence & RAG
│   │   │   ├── citation_verifier.py  # Anti-hallucination verification
│   │   │   ├── heuristic_parser.py   # 19-domain universal regex fallback
│   │   │   ├── providers.py     # Gemini, OpenAI, Anthropic, Mock providers
│   │   │   ├── schemas.py       # Pydantic extraction schemas
│   │   │   └── vector_store.py  # pgvector search wrappers
│   │   ├── chat/                # Conversational RAG
│   │   │   ├── models.py        # Conversation and Message models
│   │   │   ├── serializers.py   # Message and Citation serializers
│   │   │   ├── views.py         # Chat execution endpoints
│   │   │   └── urls.py          # /api/v1/policies/{id}/chat/
│   │   ├── clauses/             # Clause storage & categorization
│   │   │   ├── models.py        # Clause model (10+ categories)
│   │   │   ├── serializers.py   # Clause serializers
│   │   │   └── views.py         # Categorized clause retrieval
│   │   ├── core/                # Shared utilities
│   │   │   ├── exceptions.py    # Standardized DRF exception handler
│   │   │   ├── permissions.py   # IsOwner IDOR security permission
│   │   │   └── views.py         # /api/v1/health/ health check
│   │   ├── documents/           # PDF ingestion & processing
│   │   │   ├── chunker.py       # PolicyAwareChunker implementation
│   │   │   ├── models.py        # Document, DocumentPage, DocumentChunk
│   │   │   ├── parsers.py       # PyMuPDF & Tesseract OCR handlers
│   │   │   ├── tasks.py         # Celery document processing tasks
│   │   │   └── views.py         # PDF upload endpoints
│   │   └── policies/            # Policy management
│   │       ├── models.py        # Policy model (status state machine)
│   │       ├── serializers.py   # Policy serializers
│   │       ├── tasks.py         # Celery analysis coordinator task
│   │       └── views.py         # Policy CRUD and analysis triggers
│   ├── config/
│   │   ├── settings.py          # Unified Django settings
│   │   ├── urls.py              # Root URL routing & Swagger docs
│   │   ├── celery.py            # Celery application configuration
│   │   └── wsgi.py              # Gunicorn WSGI entrypoint
│   ├── Dockerfile               # Production multi-stage Python container
│   ├── pytest.ini               # Pytest test configuration
│   └── requirements.txt         # Pinned backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx         # Policy list and status overview
│   │   │   ├── HealthStatus.tsx      # System health badge & modal
│   │   │   ├── LandingPage.tsx       # Marketing & hero overview
│   │   │   ├── Login.tsx             # User authentication
│   │   │   ├── Navbar.tsx            # Navigation header
│   │   │   ├── PolicyChat.tsx        # Grounded RAG conversation interface
│   │   │   ├── PolicyOverview.tsx    # Categorized clause cards and filters
│   │   │   ├── ProcessingView.tsx    # Real-time pipeline step tracker
│   │   │   ├── Register.tsx          # Account creation
│   │   │   ├── Settings.tsx          # User preferences
│   │   │   ├── Sidebar.tsx           # Navigation drawer
│   │   │   ├── SourceViewerModal.tsx # Verifiable PDF citation inspector
│   │   │   └── UploadPolicy.tsx      # Drag-and-drop PDF upload form
│   │   ├── services/
│   │   │   └── api.ts                # Axios client with JWT interceptors
│   │   ├── types.ts                  # Shared TypeScript interfaces
│   │   ├── App.tsx                   # Main route manager
│   │   └── main.tsx                  # Vite application entrypoint
│   ├── Dockerfile                    # Production Nginx frontend container
│   ├── nginx.conf                    # Nginx reverse proxy configuration
│   ├── package.json                  # Frontend dependencies
│   └── vite.config.ts                # Vite build configuration
├── docs/                             # In-depth architectural guides
│   ├── architecture.md               # System topology and modular monolith design
│   ├── ai-pipeline.md                # RAG, chunking, and verification details
│   ├── api.md                        # Complete REST API reference
│   ├── database.md                   # Schema diagrams and pgvector queries
│   ├── deployment.md                 # Production deployment documentation
│   ├── interview-guide.md            # Technical interview Q&A
│   └── security.md                   # Threat modeling and security controls
├── .env.example                      # Environment template
├── docker-compose.yml                # Multi-container dev stack
├── docker-compose.prod.yml           # Multi-container production stack
└── README.md                         # This documentation
```

---

## 12. Database Design & Data Models

The database schema is designed for ACID compliance, referential integrity, and multi-tenant security:

```
┌──────────────────────┐
│    accounts_user     │
├──────────────────────┤
│ id (UUID / PK)       │
│ email (unique)       │
│ password (PBKDF2)    │
│ is_active (bool)     │
└──────────┬───────────┘
           │ 1:N
           ▼
┌──────────────────────┐        1:N         ┌──────────────────────┐
│   policies_policy    │───────────────────>│  documents_document  │
├──────────────────────┤                    ├──────────────────────┤
│ id (UUID / PK)       │                    │ id (UUID / PK)       │
│ user_id (FK)         │                    │ policy_id (FK)       │
│ title (varchar)      │                    │ file (varchar path)  │
│ policy_number (str)  │                    │ file_hash (SHA-256)  │
│ policy_type (enum)   │                    │ page_count (int)     │
│ status (enum)        │                    │ file_size (int)      │
└──────────┬───────────┘                    └──────────┬───────────┘
           │                                           │ 1:N
     ┌─────┴────────────────┐               ┌──────────┴───────────┐
 1:N │                  1:N │           1:N │                  1:N │
     ▼                      ▼               ▼                      ▼
┌──────────────────┐  ┌─────────────┐ ┌──────────────────┐  ┌──────────────────┐
│  clauses_clause  │  │chat_conversa│ │documents_docpage │  │documents_docchunk│
├──────────────────┤  ├─────────────┤ ├──────────────────┤  ├──────────────────┤
│ id (UUID / PK)   │  │ id (UUID)   │ │ id (UUID / PK)   │  │ id (UUID / PK)   │
│ policy_id (FK)   │  │ policy_id   │ │ document_id (FK) │  │ document_id (FK) │
│ category (enum)  │  │ user_id     │ │ page_number (int)│  │ content (text)   │
│ title (varchar)  │  └──────┬──────┘ │ cleaned_text     │  │ page_start (int) │
│ summary (text)   │         │ 1:N    │ has_ocr (bool)   │  │ page_end (int)   │
│ source_text (txt)│         ▼        └──────────────────┘  │ chunk_index (int)│
│ page_number (int)│  ┌─────────────┐                       │ embedding        │
│ confidence (flt) │  │chat_message │                       │  (VectorField    │
└──────────────────┘  ├─────────────┤                       │   dim=768)       │
                      │ id (UUID)   │                       └──────────────────┘
                      │ conv_id (FK)│
                      │ role (enum) │
                      │ content(txt)│
                      │ citations   │
                      │  (JSONB)    │
                      └─────────────┘
```

### Key Data Model Definitions

- **`User` (`apps/accounts/models.py`):** Extends `AbstractUser`, using normalized `email` as the unique username field.
- **`Policy` (`apps/policies/models.py`):** Central business record. Tracks policyholder metadata, insurance category (Health, Motor, Life, Travel, etc.), and status (`PENDING`, `ANALYZING`, `COMPLETED`, `FAILED`).
- **`Document` (`apps/documents/models.py`):** Represents the uploaded binary. Stores page count, byte size, and a unique SHA-256 hash to prevent redundant parsing jobs.
- **`DocumentPage` (`apps/documents/models.py`):** Retains raw and cleaned page-level text, along with a `has_ocr` boolean flag indicating whether the page required Tesseract recovery.
- **`DocumentChunk` (`apps/documents/models.py`):** Individual searchable text chunks with physical page coordinates (`page_start`, `page_end`) and a 768-dimensional `VectorField` indexed for cosine distance search.
- **`Clause` (`apps/clauses/models.py`):** Structured provisions extracted from the document. Each clause records its standardized category, plain-language summary, exact verbatim source quotation, physical page provenance, and confidence score.
- **`Conversation` & `Message` (`apps/chat/models.py`):** Manages multi-turn dialogue histories. Each assistant message stores structured JSON citations linking claims to specific chunk IDs and page numbers.

---

## 13. API Reference & Endpoints

All API endpoints are versioned under the `/api/v1/` prefix. Authentication requires a standard Bearer token in the `Authorization` header.

### 13.1 Authentication Endpoints

| Method | Endpoint | Description | Auth Required | Request Body | Response Body |
|---|---|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | Register a new user | No | `{"email", "username", "password", "password_confirm"}` | `{"id", "email", "username"}` |
| `POST` | `/api/v1/auth/login/` | Authenticate and obtain tokens | No | `{"email", "password"}` | `{"access", "refresh", "user"}` |
| `POST` | `/api/v1/auth/refresh/` | Refresh expired access token | No | `{"refresh"}` | `{"access"}` |
| `GET` | `/api/v1/auth/me/` | Fetch current user profile | Yes | — | `{"id", "email", "username"}` |

### 13.2 Policy & Document Endpoints

| Method | Endpoint | Description | Auth Required | Notes |
|---|---|---|---|---|
| `GET` | `/api/v1/policies/` | List all policies owned by user | Yes | Paginated (20 per page) |
| `POST` | `/api/v1/policies/` | Create a new policy record | Yes | `{"title", "policy_number", "policy_type"}` |
| `GET` | `/api/v1/policies/{id}/` | Retrieve policy details | Yes | Validates `IsOwner` |
| `DELETE` | `/api/v1/policies/{id}/` | Delete policy and all associated data | Yes | Cascade deletes documents and clauses |
| `POST` | `/api/v1/policies/{id}/documents/` | Upload policy PDF | Yes | `multipart/form-data`, key: `file` |
| `POST` | `/api/v1/policies/{id}/analyze/` | Trigger async Celery extraction | Yes | Transitions status to `ANALYZING` |
| `GET` | `/api/v1/policies/{id}/analysis/` | Poll analysis progress and status | Yes | Returns `{status, progress_percentage}` |
| `GET` | `/api/v1/policies/{id}/clauses/` | List extracted clauses | Yes | Filterable by `?category={CATEGORY}` |

### 13.3 Conversational RAG & System Endpoints

| Method | Endpoint | Description | Auth Required | Request / Response |
|---|---|---|---|---|
| `POST` | `/api/v1/policies/{id}/chat/` | Ask a question about the policy | Yes | **Req:** `{"query": "Is maternity covered?"}`<br>**Res:** `{"answer": "...", "citations": [...]}` |
| `GET` | `/api/v1/health/` | System health check | No | Returns PostgreSQL, Redis, Celery status |
| `GET` | `/api/schema/` | Download OpenAPI 3.0 YAML schema | No | Generated by drf-spectacular |
| `GET` | `/api/docs/` | Interactive Swagger UI | No | Full interactive API documentation |
| `GET` | `/api/redoc/` | Interactive Redoc documentation | No | Clean reference UI |

### 13.4 Sample Request & Response

#### Asking a Grounded Policy Question
```bash
curl -X POST http://localhost:8000/api/v1/policies/b4c139c8-3841-4777-a8a2-97cf5c84d720/chat/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the waiting period for pre-existing diseases?"}'
```

#### Verified JSON Response
```json
{
  "answer": "Under Section 4.1 (Pre-Existing Diseases), coverage for pre-existing medical conditions begins only after 36 continuous months of coverage from the policy inception date. Treatments related to these conditions during the first 36 months are strictly excluded [Page 14].",
  "citations": [
    {
      "page_number": 14,
      "source_text": "Section 4.1 Pre-Existing Diseases: Any condition, ailment or injury or related condition(s) for which there were signs or symptoms... shall be covered after thirty-six (36) months of continuous coverage.",
      "chunk_id": "8fa302cc-dc1e-4509-bca1-057d19d115a3",
      "confidence": 0.96
    }
  ],
  "verified": true
}
```

---

## 14. Asynchronous Processing & Celery Tasks

Heavy document processing and LLM calls run outside the web request cycle via Celery 5:

```
[Policy State Machine]

   ┌───────────┐
   │  PENDING  │  ← Policy created, PDF uploaded
   └─────┬─────┘
         │ Trigger POST /api/v1/policies/{id}/analyze/
         ▼
   ┌───────────┐
   │ ANALYZING │  ← Celery task active
   └─────┬─────┘
         │
         ├─── [Success] ───> ┌───────────┐
         │                   │ COMPLETED │  ← Chunks embedded, clauses persisted
         │                   └───────────┘
         │
         └─── [Exception] ─> ┌───────────┐
                             │  FAILED   │  ← Error logged, safe message recorded
                             └───────────┘
```

### Task Specifications

1. **`process_document(document_id)` (`apps/documents/tasks.py`):**
   - Reads the PDF binary from storage.
   - Executes PyMuPDF page-by-page extraction with Tesseract OCR fallback.
   - Executes `PolicyAwareChunker`.
   - Generates 768-dimensional embeddings and performs a bulk database insert.
2. **`analyze_policy_task(policy_id)` (`apps/policies/tasks.py`):**
   - Coordinates chunk retrieval for the policy.
   - Invokes structured extraction via the configured `LLM_PROVIDER`.
   - Executes `HeuristicPolicyParser` if LLM extraction yields zero results.
   - Passes extracted clauses through `CitationVerifier`.
   - Commits verified clauses in a single atomic database transaction (`transaction.atomic()`).
   - Updates policy status to `COMPLETED`.

---

## 15. Security & Multi-Tenancy Architecture

PolicyLens AI enforces defence-in-depth across all system layers:

### 15.1 Stateless Authentication & Token Rotation
- Utilizes `rest_framework_simplejwt` with `HS256` HMAC signing.
- **Short-lived access tokens:** 60-minute expiration limits the blast radius of token compromise.
- **Rotating refresh tokens:** 7-day expiration with token rotation on refresh requests (`ROTATE_REFRESH_TOKENS = True`).

### 15.2 Insecure Direct Object Reference (IDOR) Prevention
- Direct model queries are strictly scoped to the authenticated user.
- The `IsOwner` permission class (`apps/core/permissions.py`) intercepts every object-level request:
  ```python
  class IsOwner(permissions.BasePermission):
      def has_object_permission(self, request, view, obj):
          if hasattr(obj, "user"):
              return obj.user == request.user
          if hasattr(obj, "policy"):
              return obj.policy.user == request.user
          return False
  ```

### 15.3 File Upload Security
- **MIME & Extension Enforcement:** Rejects any upload without a `.pdf` extension.
- **Magic Byte Verification:** Inspects the first 4 bytes of the binary to guarantee `%PDF-` compliance, blocking disguised executables.
- **Size Bounds:** Enforces an unyielding 25 MB file limit (`MAX_UPLOAD_SIZE_MB`).
- **Filename Sanitization:** Files are assigned cryptographically random UUID storage paths, preventing path traversal attacks (`../../etc/passwd`).
- **SHA-256 Collision Check:** Computes document hashes to prevent duplicate ingestion and disk exhaustion.

### 15.4 Privacy-Safe Logging & Header Hardening
- Loggers are configured to strip personally identifiable information (PII), raw policy text, and API keys.
- Production settings enforce `SECURE_CONTENT_TYPE_NOSNIFF = True`, `X_FRAME_OPTIONS = "DENY"`, and strict HSTS headers (`SECURE_HSTS_SECONDS = 31536000`).

---

## 16. Reliability, Resilience & Edge Cases

The system is designed to handle messy real-world document artifacts and third-party API instability:

- **Scanned / Image-Only PDFs:** Pages containing scanned forms or photos trigger high-resolution rasterization and Tesseract OCR automatically when character count drops below 40.
- **Corrupted PDF Streams:** PyMuPDF error boundaries intercept truncated or malformed PDF files, recording a user-visible validation error without crashing worker processes.
- **LLM Outages & Quota Depletion:** If Gemini or OpenAI API endpoints encounter rate limits (HTTP 429), timeouts, or service errors, the pipeline triggers the `HeuristicPolicyParser` fallback. This rule-based engine extracts coverages, exclusions, and deductibles using regex section patterns across 19 standard insurance domains.
- **Database Consistency:** Clause writes and status transitions are wrapped in `transaction.atomic()`. If an unhandled exception occurs mid-write, partial extractions roll back cleanly, and the policy transitions to `FAILED`.

---

## 17. Testing & Quality Assurance

PolicyLens AI maintains a comprehensive, deterministic test suite executed via Pytest.

### 17.1 Test Suite Verification
**Verified Test Count:** **102 tests passed, 0 failures** in pytest.

The suite covers all critical system paths:
- **Authentication & JWT Lifecycle (`apps/accounts/test_auth.py`):** Registration, password confirmation checks, token generation, refresh rotation, and invalid credential rejections.
- **Policy CRUD & Ownership (`apps/policies/test_views.py`, `test_models.py`):** Status transitions, multi-tenant isolation, cascade deletions.
- **Document Ingestion & Chunking (`apps/documents/test_*.py`):** Magic byte validation, SHA-256 deduplication, PyMuPDF parsing, OCR fallback, and `PolicyAwareChunker` heading preservation.
- **Clause Extraction & Storage (`apps/clauses/test_*.py`):** 10+ category classifications, page number assignments, and confidence thresholds.
- **Grounded Chat & Citation Verification (`apps/chat/test_*.py`, `apps/ai_engine/test_*.py`):** Anti-hallucination validation, pgvector cosine search scoping, and ungrounded response rejection.
- **Regression Testing (`apps/policies/test_sample_policy_regression.py`):** End-to-end regression validation against sample insurance policy structures.
- **System Core & Health (`apps/core/test_*.py`):** Multi-service health checks, custom exception handlers, and IDOR permissions.

### 17.2 Running Tests

#### Run full test suite inside Docker:
```bash
docker compose exec backend pytest -v
```

#### Run tests locally with coverage:
```bash
cd backend
pytest -v --cov=apps --cov-report=term-missing
```

#### Run linting via Ruff (0 errors):
```bash
ruff check apps/ --exclude '*/migrations/*.py'
```

---

## 18. Local Development Setup (Without Docker)

For active local development without container virtualization:

### 18.1 Prerequisites
- **Python:** Version 3.12+
- **Node.js:** Version 20+ and `npm`
- **PostgreSQL:** Version 16 with the `pgvector` extension installed
- **Redis:** Version 7+
- **Tesseract OCR:** Installed on system PATH (`tesseract --version`)

### 18.2 Backend Setup

1. **Navigate to the backend directory and create a virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure local environment variables:**
   ```bash
   # From repository root:
   cp .env.example .env
   ```
   *Update `POSTGRES_HOST=localhost`, `POSTGRES_PASSWORD`, and `LLM_PROVIDER`.*

4. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Start Celery worker (in a separate terminal):**
   ```bash
   celery -A config worker -l info --concurrency=2
   ```

6. **Start Django development server:**
   ```bash
   python manage.py runserver 8000
   ```

### 18.3 Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Start Vite development server:**
   ```bash
   npm run dev
   ```
   *The SPA is accessible at `http://localhost:5173`.*

---

## 19. Environment Variables Reference

| Variable Name | Required | Default Value | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes** | — | Cryptographic secret key used for session and JWT signing |
| `DJANGO_DEBUG` | No | `False` | Django debug mode. Must be `False` in production |
| `DJANGO_ALLOWED_HOSTS` | No | `localhost,127.0.0.1,backend` | Comma-separated list of valid Host header domains |
| `POSTGRES_DB` | No | `policylens_db` | PostgreSQL database name |
| `POSTGRES_USER` | No | `policylens_user` | PostgreSQL database username |
| `POSTGRES_PASSWORD` | **Yes** | — | PostgreSQL user password |
| `POSTGRES_HOST` | No | `postgres` (`localhost` for local dev) | Database host address |
| `POSTGRES_PORT` | No | `5432` | Database port |
| `POSTGRES_EXTERNAL_PORT`| No | `5433` | Host port mapped to Postgres container in Compose |
| `REDIS_URL` | No | `redis://redis:6379/0` | Connection URL for Redis cache and Celery broker |
| `LLM_PROVIDER` | No | `mock` | Active provider: `mock`, `gemini`, `openai`, `anthropic`, `local` |
| `GEMINI_API_KEY` | Conditional | — | Required if `LLM_PROVIDER=gemini` |
| `OPENAI_API_KEY` | Conditional | — | Required if `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | Conditional | — | Required if `LLM_PROVIDER=anthropic` |
| `EMBEDDING_MODEL` | No | `text-embedding-3-small` | Default embedding model identifier |
| `MAX_UPLOAD_SIZE_MB` | No | `25` | Maximum PDF file upload size in megabytes |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost,http://localhost:5173` | Allowed frontend origins for CORS headers |

---

## 20. Docker & Containerized Setup

The Docker Compose configuration provisions the entire five-service architecture with a single command:

### 20.1 Quick Launch

1. **Clone the repository and copy the environment template:**
   ```bash
   git clone https://github.com/Surendra571/policylens-ai.git
   cd policylens-ai
   cp .env.example .env
   ```

2. **Edit `.env` to configure your credentials:**
   ```env
   DJANGO_SECRET_KEY=your-secure-random-secret-key-at-least-50-characters
   POSTGRES_PASSWORD=your-secure-db-password
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your-gemini-api-key
   ```
   *(Set `LLM_PROVIDER=mock` if running without external AI API keys).*

3. **Build and start all services:**
   ```bash
   docker compose build
   docker compose up -d
   ```

4. **Verify container status:**
   ```bash
   docker compose ps
   ```
   *All containers should indicate `healthy` status.*

5. **Access the application:**
   - **Frontend Application:** `http://localhost`
   - **Backend Health Check:** `http://localhost:8000/api/v1/health/`
   - **Swagger API Documentation:** `http://localhost:8000/api/docs/`

---

## 21. Production Deployment Guide

For production deployments on cloud virtual machines (Ubuntu / Debian VPS, AWS EC2, DigitalOcean Droplet, Hetzner):

### 21.1 Production Compose Stack

The repository includes `docker-compose.prod.yml` configured for hardened production workloads:
- `DJANGO_DEBUG=False` enforced.
- Static assets pre-collected into an isolated volume and served directly by Nginx.
- Backend WSGI workers managed by Gunicorn with auto-restart worker recycling.
- Nginx configured with reverse proxy timeouts appropriate for large PDF uploads.

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### 21.2 SSL / TLS Termination

Place an external reverse proxy (Caddy, Traefik, or Nginx with Let's Encrypt Certbot) in front of port `80`:

```nginx
server {
    server_name policylens.yourdomain.com;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl;
    # SSL certificates managed via Certbot
}
```

---

## 22. Configuration & Model Switching

PolicyLens AI supports multiple AI backends via a unified provider interface (`apps/ai_engine/providers.py`). Switch providers dynamically via the `LLM_PROVIDER` environment variable:

```bash
# 1. Google Gemini (Recommended for production cost/performance)
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...

# 2. OpenAI GPT-4o / text-embedding-3-small
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# 3. Anthropic Claude 3.5 Sonnet
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# 4. Deterministic Mock Provider (Zero API cost, offline testing & CI)
LLM_PROVIDER=mock
```

*Note: After updating `.env`, restart the backend and Celery containers:*
```bash
docker compose up -d backend celery_worker
```

---

## 23. UI Tour & Component Walkthrough

The React 19 single-page application provides a responsive workflow for analyzing insurance policies:

1. **Landing & Marketing View (`LandingPage.tsx`):** Overview of platform capabilities, security guarantees, and quick onboarding.
2. **Authentication Flow (`Login.tsx`, `Register.tsx`):** Secure user registration and login with automatic JWT storage in local storage and Axios request interceptors.
3. **Policy Dashboard (`Dashboard.tsx`, `Sidebar.tsx`):** Displays all active and past uploaded policies with metadata badges (Policy Number, Category, Processing Status).
4. **Drag-and-Drop Ingestion (`UploadPolicy.tsx`):** Clean file upload interface with immediate client-side file size and extension verification.
5. **Real-Time Pipeline Tracker (`ProcessingView.tsx`):** Visual step-by-step progress monitor showing extraction, OCR, chunking, and clause generation states.
6. **Categorized Clause Browser (`PolicyOverview.tsx`):** Interactive card layout grouping extracted clauses into Coverages, Exclusions, Waiting Periods, Sub-Limits, and Deductibles with search and filter controls.
7. **Conversational Grounded Chat (`PolicyChat.tsx`):** Multi-turn conversational interface with typing indicators, markdown response formatting, and clickable citation tags.
8. **Verifiable PDF Source Inspector (`SourceViewerModal.tsx`):** Clicking any `[Page X]` badge opens an overlay displaying the exact text snippet stored in PostgreSQL for that page.
9. **System Health Status (`HealthStatus.tsx`):** Real-time indicator displaying PostgreSQL, Redis, and Celery connectivity status.

---

## 24. Engineering Decisions & Architecture Trade-Offs

| Decision | Alternative Considered | Rationale & Trade-Off |
|---|---|---|
| **Modular Monolith** | Microservices Architecture | Avoided premature distribution. Monolith guarantees atomic database transactions across policies and clauses, simplifies tenant isolation, and eliminates cross-service network latency. |
| **PostgreSQL + `pgvector`** | Dedicated Vector DB (Pinecone, Weaviate, Qdrant) | Storing 768d vectors in PostgreSQL allows relational joins between chunks, documents, and policies. Eliminates data synchronization drift and removes a separate database infrastructure dependency. |
| **Celery + Redis** | Background Python Threads / asyncio | Threads fail silently if the web process crashes or restarts during long OCR jobs. Celery guarantees task durability, worker concurrency management, and distributed retry mechanisms. |
| **PyMuPDF (`fitz`)** | `pdfplumber` / `pypdf` | PyMuPDF executes native C bindings, delivering 10x to 20x faster page extraction speeds and superior layout/coordinate preservation. |
| **Pydantic v2 Schema Enforcement** | Unstructured Prompt Output | LLMs are non-deterministic. Enforcing Pydantic schemas ensures that extractions strictly match domain models before database persistence. |
| **Database Citation Verification** | Trusting LLM References | Generative models frequently fabricate believable citations. The `CitationVerifier` guarantees mathematical certainty by verifying that cited text exists verbatim in PostgreSQL. |

---

## 25. Current Limitations & Known Constraints

To maintain technical integrity, we explicitly document current system limitations:

- **Synchronous RAG Chat Execution:** The document analysis pipeline runs asynchronously via Celery, but conversational chat queries execute synchronously within the HTTP request cycle. Responses typically return in 1 to 3 seconds depending on the external LLM provider's latency.
- **OCR Processing Time on Scanned Documents:** While native digital PDFs process in seconds, scanned image PDFs requiring full-page Tesseract OCR at 300 DPI take approximately 1 to 2 seconds per page. A 60-page scanned policy may require 1 to 2 minutes of background processing.
- **Single Active Document per Policy:** The current UI workflow associates one active primary PDF policy schedule per policy record. Multi-document bundles (e.g. separate policy wording booklet + schedule endorsement) must be uploaded as distinct policies.
- **Deterministic Mock Provider Scope:** The `mock` LLM provider generates deterministic hashes and structured mock clauses for offline testing without external API keys. It does not perform real semantic inference.

---

## 26. Roadmap & Future Scope

- [ ] **Multi-Document Comparison Matrix:** Side-by-side comparison of two competing policies (e.g. Star Health vs HDFC ERGO) with automated coverage and exclusion diffing.
- [ ] **Asynchronous Streaming Chat:** Server-Sent Events (SSE) or WebSockets integration for real-time word-by-word streaming during RAG generation.
- [ ] **Automated Claim Eligibility Check:** Upload an itemized medical discharge summary or repair estimate to automatically assess claim validity against policy sub-limits and exclusions.
- [ ] **Multilingual Support:** Translation and parsing of regional Indian and European policy documents according to local regulatory standards (e.g. IRDAI circulars).
- [ ] **HNSW Vector Indexing:** Transition from IVFFlat to HNSW indexing in `pgvector` for sub-millisecond retrieval across millions of policy chunks.

---

## 27. Real-World Use Cases & Sample Scenarios

### Scenario 1: Health Insurance Pre-Existing Disease Check
- **User Query:** *"I was diagnosed with hypertension two years ago. If I am hospitalized for a related complication, will this policy cover my expenses?"*
- **PolicyLens AI Output:** Identifies Section 4.1 in the exclusion schedule, notes the 36-month waiting period for pre-existing conditions, computes that 24 months have elapsed, and flags that coverage will not apply until the 36-month threshold is reached, citing **[Page 18]**.

### Scenario 2: Motor Insurance Zero-Depreciation Exclusion
- **User Query:** *"Does my comprehensive auto policy cover full replacement of plastic and rubber parts during an accident claim?"*
- **PolicyLens AI Output:** Locates the Depreciation Schedule under Section 2, notes that rubber and nylon parts incur a 50% depreciation deduction unless the Zero Depreciation add-on endorsement is active, citing **[Page 6]**.

### Scenario 3: Travel Insurance Baggage Delay
- **User Query:** *"My baggage was delayed for 8 hours on an international flight. Can I claim compensation for emergency clothes?"*
- **PolicyLens AI Output:** Retrieves Section 5.3 (Baggage Delay), verifies that the deductible is 12 hours of delay, and clarifies that an 8-hour delay does not meet the eligibility threshold, citing **[Page 32]**.

---

## 28. Troubleshooting & FAQ

### Q: Why is my policy analysis stuck in `ANALYZING`?
**A:** Check your Celery worker logs. The worker may not be running or may be unable to reach Redis:
```bash
docker compose logs celery_worker -f
```

### Q: Why do I get a database connection error during local development?
**A:** If running Django locally outside Docker while PostgreSQL is in Docker, ensure `.env` has:
```env
POSTGRES_HOST=localhost
POSTGRES_EXTERNAL_PORT=5433
```
*(Inside Docker, `POSTGRES_HOST` must be `postgres`)*.

### Q: Extraction yields 0 clauses with an external LLM provider. Why?
**A:** Verify that your API key is valid and has not exceeded quota:
```bash
docker compose exec backend python -c "
import os
from apps.ai_engine.providers import get_llm_provider
provider = get_llm_provider()
print(provider.generate('Ping'))
"
```
If the API fails, the system automatically engages the `HeuristicPolicyParser` fallback.

### Q: How do I rebuild after modifying backend Python code?
**A:** In Docker, backend dependencies and code are baked into the container. Rebuild and restart:
```bash
docker compose build backend celery_worker
docker compose up -d backend celery_worker
```

---

## 29. Contributing

Contributions to PolicyLens AI are welcome. Please follow these guidelines:

1. **Fork the repository** on GitHub.
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/insurance-comparison-matrix
   ```
3. **Ensure strict code quality and formatting:**
   ```bash
   # Run Ruff linter
   ruff check apps/ --exclude '*/migrations/*.py'
   # Run full test suite
   pytest -v
   ```
4. **Commit your changes with descriptive commit messages:**
   ```bash
   git commit -m "feat(clauses): add IRDAI standard waiting period categorization"
   ```
5. **Push to your branch and open a Pull Request.**

---

## 30. License

PolicyLens AI is distributed under the open-source **MIT License**.  
See the [LICENSE](LICENSE) file for full details.

---

<div align="center">
  <sub>Engineered with precision for InsurTech reliability. Built with Django, Celery, pgvector, and React.</sub>
</div>
