# Architecture Guide: PolicyLens AI

## 1. System Topology & Architectural Philosophy

PolicyLens AI is engineered as a **modular monolith** running Django 5, Celery, Redis, and PostgreSQL with the `pgvector` extension, coupled with a reactive TypeScript SPA. 

```
                                    +------------------------------+
                                    |       React 19 Frontend      |
                                    | (Vite / TypeScript / Tailwind)|
                                    +--------------+---------------+
                                                   |
                                            Reverse Proxy (Nginx)
                                                   |
                                    +--------------v---------------+
                                    |    Django REST Framework API  |
                                    |      (Gunicorn / WSGI)       |
                                    +-------+--------------+-------+
                                            |              |
                    +-----------------------+              +------------------------+
                    |                                                               |
        +-----------v-----------+                                      +------------v------------+
        |  PostgreSQL 16 DB    |                                      |      Redis 7 Broker      |
        |  + pgvector extension |                                      |   & Distributed Cache   |
        +-----------------------+                                      +------------+------------+
                                                                                    |
                                                                       +------------v------------+
                                                                       |   Celery Worker Cluster  |
                                                                       | (OCR / Chunking / RAG)  |
                                                                       +-------------------------+
```

### Why a Modular Monolith?
- **Domain Boundaries Without Distributed Latency:** Each core business concern (`accounts`, `policies`, `documents`, `clauses`, `chat`, `ai_engine`, `core`) is an isolated Django application with strict model ownership and foreign-key isolation.
- **Transactional Integrity:** Complex document updates and clause ingestion can be committed atomically in PostgreSQL (`transaction.atomic()`).
- **Simpler Security Posture:** Eliminates distributed identity propagation; JWT claims are evaluated once at the perimeter and enforced via Django ORM row-level query filtering.

---

## 2. Component Responsibilities

### `apps.accounts`
- Manages user lifecycle, PBKDF2 password hashing, and stateless JWT token issuance/rotation via `rest_framework_simplejwt`.

### `apps.policies`
- Encapsulates insurance policy metadata, plan types, and coordinates processing workflows (`analyze_policy` Celery task).

### `apps.documents`
- Handles PDF upload validation, SHA-256 duplicate detection, physical storage abstraction, text extraction via PyMuPDF with Tesseract OCR fallback, policy-aware chunking, and vector embedding generation.

### `apps.clauses`
- Stores extracted and structured clauses (Coverage, Exclusion, Waiting Period, Deductible, Limit, Condition, Claim Requirement) along with verbatim source quotations and physical document page provenance.

### `apps.chat`
- Coordinates user conversation sessions, message history, and strictly grounded citations mapped to physical PDF pages.

### `apps.ai_engine`
- Encapsulates provider abstractions (`OpenAI`, `Gemini`, `Mock`), deterministic and semantic embedding services, policy-scoped retrieval (leveraging native PostgreSQL `pgvector`), prompt templates, and the non-negotiable `CitationVerifier`.

---

## 3. Data & Execution Lifecycle

```
1. Upload PDF  ──> 2. Validation & SHA256  ──> 3. Celery Ingestion  ──> 4. PyMuPDF / OCR
                                                                                │
7. Policy-Scoped RAG <── 6. pgvector Storage <── 5. Policy-Aware Chunking <─────┘
        │
8. Grounded LLM Response ──> 9. Citation Verification ──> 10. User Response
```

1. **PDF Ingestion:** Uploaded file is validated for MIME type (`application/pdf`), magic bytes (`%PDF-`), and file size ($\le 20\text{ MB}$).
2. **Extraction & OCR:** PyMuPDF parses page-by-page text. Pages with fewer than 40 characters trigger an automatic OCR fallback using Tesseract.
3. **Policy-Aware Chunking:** Chunks maintain structural boundaries (headings, numbered clauses, tables) rather than slicing blind character offsets.
4. **Embedding Generation:** Vectors (768 dimensions) are computed in batches and persisted into the `DocumentChunk.embedding` column.
5. **Database-Side Similarity:** Query embeddings search the policy's chunks directly inside PostgreSQL using the `CosineDistance` operator (`<=>`).
6. **Anti-Hallucination & Verification:** Retrieved context is injected into strict system prompts. The model's returned citations are verified by `CitationVerifier` against actual database chunks before display.
