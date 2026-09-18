# API Documentation: PolicyLens AI

## Base URL
`/api/v1`

All responses use JSON format and standard HTTP status codes.

---

## 1. Authentication (`/api/v1/auth/`)

### Register
`POST /api/v1/auth/register/`
```json
// Request
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!",
  "first_name": "Jane",
  "last_name": "Doe"
}

// Response: 201 Created
{
  "success": true,
  "user": {
    "id": "c1f7b8...-uuid",
    "email": "user@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "tokens": {
    "access": "eyJhbGciOi...",
    "refresh": "eyJhbGciOi..."
  }
}
```

### Login
`POST /api/v1/auth/login/`
```json
// Request
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}

// Response: 200 OK
{
  "success": true,
  "user": { ... },
  "tokens": {
    "access": "eyJhbGciOi...",
    "refresh": "eyJhbGciOi..."
  }
}
```

---

## 2. Policies (`/api/v1/policies/`)

### List Policies
`GET /api/v1/policies/`
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK` (strictly scoped to the requesting user's policies).

### Create Policy
`POST /api/v1/policies/`
```json
{
  "name": "Optima Secure Health",
  "provider": "HDFC ERGO",
  "policy_type": "INDIVIDUAL"
}
```

### Upload Policy PDF
`POST /api/v1/policies/{id}/documents/`
- **Content-Type:** `multipart/form-data`
- **Rate Limit:** 10 requests / minute / user (`DocumentUploadThrottle`)
- **Payload:** `file: <binary PDF>`

### Trigger Policy Analysis
`POST /api/v1/policies/{id}/analyze/`
- **Rate Limit:** 10 requests / minute / user (`PolicyAnalysisThrottle`)
- **Response:** `202 Accepted`
```json
{
  "success": true,
  "message": "Policy analysis initiated asynchronously.",
  "policy_id": "8f2a...-uuid",
  "status": "ANALYZING"
}
```

### Poll Analysis Results
`GET /api/v1/policies/{id}/analysis/`
- **Response:** `200 OK` (returns full analysis summary, categorized clauses, and highlighted key points with page provenance).

---

## 3. Grounded Chat (`/api/v1/policies/{id}/chat/`)

### Ask Your Policy
`POST /api/v1/policies/{id}/chat/`
- **Rate Limit:** 30 requests / minute / user (`PolicyChatThrottle`)
```json
// Request
{
  "question": "Is maternity expenses covered?",
  "conversation_id": "optional-uuid-to-continue-thread"
}

// Response: 200 OK
{
  "conversation_id": "99b0c...-uuid",
  "question": "Is maternity expenses covered?",
  "answer": "Yes, maternity expenses are covered up to INR 50,000 after a waiting period of 24 months of continuous coverage.",
  "confidence": "high",
  "citations": [
    {
      "chunk_id": "a1b2c3...-uuid",
      "page": 12,
      "section": "Maternity Benefits",
      "source_text": "Maternity expenses are covered up to INR 50,000 after a waiting period of 24 months of continuous coverage.",
      "policy": "Optima Secure Health",
      "document": "optima_secure.pdf",
      "verified": true
    }
  ]
}
```

---

## 4. System Health Check (`/api/v1/health/`)

### Health Endpoint
`GET /api/v1/health/`
- **Permission:** AllowAny (Unauthenticated)
- **Response:** `200 OK` (or `503 Service Unavailable` if core components fail)
```json
{
  "status": "healthy",
  "service": "policylens-ai-backend",
  "version": "1.0.0",
  "timestamp": "2026-09-18T14:58:01.403924+00:00",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "cache": "healthy",
    "celery": "healthy"
  }
}
```

