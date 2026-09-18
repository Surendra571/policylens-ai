# Security Architecture & Data Isolation: PolicyLens AI

## 1. Security Tenets

In InsurTech applications, confidential policy schedules contain private financial and healthcare information. PolicyLens AI enforces a zero-trust architecture ensuring **strict tenant isolation**, **anti-IDOR enforcement**, and **zero sensitive data leakage**.

---

## 2. Authentication & JWT Life Cycle

- **Standard:** Stateless JSON Web Tokens (`rest_framework_simplejwt`).
- **Signature:** HMAC-SHA256 with key rotated from `DJANGO_SECRET_KEY`.
- **Token Lifetimes:** 60-minute Access Token, 7-day Refresh Token.
- **Header Structure:** `Authorization: Bearer <access_token>`.

---

## 3. IDOR & Multi-Tenant Authorization

Every database query accessing user data enforces row-level user ownership checks:

```python
class PolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        # Strict user-level scoping
        return Policy.objects.filter(user=self.request.user).prefetch_related("documents")
```

### Isolated Boundary Matrix

| Resource | Scope Restriction | Violation Response |
| :--- | :--- | :--- |
| **Policies** | `Policy.objects.filter(user=request.user)` | `404 Not Found` |
| **Documents** | `Document.objects.filter(policy__user=request.user)` | `404 Not Found` |
| **Chunks & Pages** | `DocumentChunk.objects.filter(document__policy__user=request.user)` | `404 Not Found` |
| **Clauses** | `Clause.objects.filter(policy__user=request.user)` | `404 Not Found` |
| **Conversations** | `Conversation.objects.filter(user=request.user)` | `404 Not Found` |
| **RAG Queries** | Enforces `if policy.user != user: raise PermissionError` | `403 Forbidden` |

---

## 4. Input & File Upload Security

1. **Magic Header Byte Verification:** Reads raw initial buffer to verify `%PDF-` signature; files claiming `.pdf` extension with fake binary headers are rejected with `400 Bad Request`.
2. **File Size Hard Limit:** Enforced at $20\text{ MB}$ (configurable via `MAX_UPLOAD_SIZE_MB`).
3. **Filename Sanitization:** Strips path traversal sequences (`../`, `..\\`), null bytes (`%00`), and non-alphanumeric characters.
4. **Duplicate Prevention:** Computes SHA-256 hash of PDF binary contents before persisting to disk.

---

## 5. Rate Limiting & Throttling

Dedicated throttles configured in `apps.core.throttles`:
- **Document Upload:** $10\text{ req/min/user}$ (`DocumentUploadThrottle`)
- **Policy Analysis:** $10\text{ req/min/user}$ (`PolicyAnalysisThrottle`)
- **Policy Chat:** $30\text{ req/min/user}$ (`PolicyChatThrottle`)
- **Unauthenticated:** $120\text{ req/min/IP}$

---

## 6. Privacy-Safe Observability

- Logs never record extracted policy text, raw OCR buffers, prompt contexts, or user credentials.
- All events use surrogate foreign keys (`policy_id`, `document_id`, `task_id`).
- Health endpoints return status indicators (`healthy`, `degraded`, `unavailable`) without exposing connection strings, hosts, or tracebacks.

