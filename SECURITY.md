# PolicyLens AI Security Model & Architecture (`SECURITY.md`)

## 1. Security Overview
PolicyLens AI processes sensitive insurance policies, personal health coverage contracts, and claim histories. The platform adheres to a **Zero-Trust, Defense-in-Depth** security architecture ensuring confidentiality, integrity, availability, and strict tenant isolation across all layers.

---

## 2. Authentication & Authorization Architecture

### Authentication
- **Password Security**: Passwords are hashed using Django's standard PBKDF2 with SHA-256 (or Argon2) with automatic salting. Passwords must pass similarity, length, common-password, and numeric validation.
- **JWT (JSON Web Tokens)**:
  - Ephemeral Access Tokens (60-minute lifetime).
  - Refresh Tokens (7-day lifetime) with automatic token rotation.
  - Signed cryptographically using `HS256` with secure server-side secrets.
  - Transmitted via `Authorization: Bearer <token>` headers.
- **Session Security**: Session cookies and CSRF tokens are flagged `Secure`, `HttpOnly`, and `SameSite=Lax` in production environments.

### Strict IDOR Prevention & Tenant Isolation
User A must **never** be capable of accessing, viewing, modifying, or querying:
- User B's policies
- User B's uploaded PDF files
- User B's document pages & text chunks
- User B's extracted insurance clauses
- User B's AI conversations & messages

**Enforcement Mechanisms**:
1. **Queryset Scoping**: Every ViewSet (`PolicyViewSet`, `DocumentViewSet`, `ClauseViewSet`, `ConversationViewSet`, `MessageViewSet`) filters strictly by `request.user`:
   ```python
   def get_queryset(self):
       return Policy.objects.filter(user=self.request.user)
   ```
2. **Object-Level Permissions**: The custom `IsOwner` permission traverses the entire object hierarchy (`obj.user`, `obj.policy.user`, `obj.document.policy.user`, `obj.conversation.user`).
3. **Cross-Tenant Status Codes**: Unowned resource requests return `404 Not Found` (or `403 Forbidden`) to prevent resource enumeration attacks.

---

## 3. Secure File Upload & Document Ingestion Pipeline

### Upload Safeguards
- **File Type & Extension**: Only `.pdf` files are permitted.
- **MIME-Type Validation**: Validated against `application/pdf`.
- **Magic Byte Inspection**: The file header must explicitly begin with `%PDF` signature bytes; disguised executables or text files are rejected immediately.
- **Malicious PDF Inspection**: Uploads are scanned for dangerous launch actions (`/Launch`, `/EmbeddedFiles`, `/JavaScript`) to prevent executable PDF payload attacks.
- **File Size Limits**: Configurable via `MAX_UPLOAD_SIZE_MB` (default 20MB); uploads exceeding the limit are rejected before disk buffering.
- **Path Traversal Prevention**: Filenames are sanitized with `sanitize_filename()`, stripping both forward slashes (`/`), backward slashes (`\`), null bytes (`\x00`), and leading dots (`.`), generating clean alphanumeric identifiers.
- **SHA-256 Deduplication**: Identical PDFs uploaded within the same policy are detected via SHA-256 content hashing.

### Asynchronous Processing
- PDF parsing, OCR fallback, text cleaning, chunking, and AI analysis are executed asynchronously via Celery background workers.
- No synchronous PDF execution occurs in the request-response cycle, protecting the API from DoS attacks via large files.

---

## 4. RAG Data Isolation & Anti-Hallucination Guardrails

### Tenant & Policy Isolation in Retrieval
- Vector similarity and lexical keyword retrieval **never** query globally across policies.
- Every retrieval query strictly scopes chunks by `document__policy=policy` where `policy.user == request.user`.
- Cross-policy vector retrieval raises a `PermissionError`.

### Citation Integrity & Immutability (`CitationVerifier`)
- **Real Page Guarantee**: Every citation returned by RAG must resolve to an authentic `DocumentPage` and `DocumentChunk` in the database.
- **Anti-Fabrication**: The AI cannot invent fake page numbers (e.g. Page 99 on an 18-page document). Mismatched page numbers cause the citation to be dropped.
- **Verbatim Immutability**: The original policy text in the evidence viewer is **never** generated or rewritten by the LLM. It is pulled directly from the database record.
- **Unresolved Dropping**: If a citation cannot be verified, it is omitted. If no citations are verified, PolicyLens AI returns:
  > *"I couldn't find enough information about this in your policy document."*

---

## 5. Network, Web & Injection Defenses

| Threat Category | Mitigation |
| :--- | :--- |
| **SQL Injection** | Exclusively parameterized queries via Django ORM and pgvector extension. Zero raw string concatenation. |
| **Cross-Site Scripting (XSS)** | React JSX automatic DOM escaping; JSON-only API outputs; `SECURE_BROWSER_XSS_FILTER = True`. |
| **Cross-Site Request Forgery (CSRF)** | Token-based stateless authentication (`Authorization: Bearer`); CSRF middleware enabled. |
| **Clickjacking** | `X_FRAME_OPTIONS = "DENY"`. |
| **Content Sniffing** | `SECURE_CONTENT_TYPE_NOSNIFF = True`. |
| **Transport Security** | `SECURE_SSL_REDIRECT = True` and HSTS enabled in production (`SECURE_HSTS_SECONDS = 31536000`). |
| **CORS** | Strict whitelist origin validation via `CORS_ALLOWED_ORIGINS`. |
| **Rate Limiting (DoS)** | DRF Throttling: `120 requests/minute` for anonymous clients, `1200 requests/minute` for authenticated users. |

---

## 6. Privacy-Preserving Logging & Secrets Management

### Logging Protocol
- **Strict No-PII Rule**: Logs never record:
  - Private policy text or clauses
  - Personally Identifiable Information (PII)
  - Full LLM prompts containing user documents
  - User passwords or raw JWT tokens
- **Auditable Traceability**: Logs only record anonymized UUIDs, status transitions, and operation counts:
  ```
  [2026-09-17 13:50:00] INFO in apps.documents.tasks: Document ID 3fa85f64: Successfully extracted 12 pages.
  ```

### Secrets Management
- Application secrets (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_URL`, `GEMINI_API_KEY`, `OPENAI_API_KEY`) are managed exclusively through environment variables and `.env` files.
- Version control excludes all credentials, SQLite databases, and `.env` files.

---

## 7. Security Verification & Test Suite
The security model is verified by automated pytest suites:
- `apps/core/test_authorization.py`: Validates IDOR prevention across all models, preventing cross-user reads, updates, and deletes.
- `apps/policies/test_policy_and_upload.py`: Validates file size limits, MIME validation, magic byte checks, and duplicate rejection.
- `apps/chat/test_policy_chat.py`: Validates tenant isolation in policy AI chat.
- `apps/ai_engine/test_citation_integrity.py`: Validates anti-fabrication, fake page rejection, and citation immutability.

