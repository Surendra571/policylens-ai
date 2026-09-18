# AI & Grounded RAG Pipeline: PolicyLens AI

## 1. End-to-End Pipeline Architecture

```
                                  +----------------------------+
                                  |    Uploaded Policy PDF     |
                                  +--------------+-------------+
                                                 |
                                     1. Extraction & OCR
                                                 |
                                  +--------------v-------------+
                                  |   Page-by-Page Extraction  |
                                  |   (PyMuPDF + Tesseract)    |
                                  +--------------+-------------+
                                                 |
                                     2. Policy-Aware Chunker
                                                 |
                                  +--------------v-------------+
                                  |  Semantic Headings/Clauses |
                                  |  Boundaries & Page Numbers |
                                  +--------------+-------------+
                                                 |
                                     3. Embedding Generation
                                                 |
                                  +--------------v-------------+
                                  | pgvector (768 Dimensions)  |
                                  |   PostgreSQL Cosine Index  |
                                  +--------------+-------------+
                                                 |
              +----------------------------------+----------------------------------+
              |                                                                     |
     Structured Policy Analysis                                            Grounded Policy Chat
              |                                                                     |
  4. Multi-Chunk Extraction                                              4. Question Embedding
              |                                                                     |
  5. Pydantic Schema Validation                                          5. pgvector SQL Search
     (PolicyAnalysis)                                                    (Filtered by Policy ID)
              |                                                                     |
  6. Anti-Hallucination Guard                                            6. Evidence Sufficiency Gate
     (Verbatim Source Check)                                                        |
              |                                                          7. Grounded LLM Prompt
  7. Persist to Clause Table                                                        |
                                                                         8. CitationVerifier
                                                                            (Database Verification)
                                                                                    |
                                                                         9. Verified Answer + Cites
```

---

## 2. Ingestion & Preprocessing

- **Direct Extraction:** `fitz.open(stream=bytes)` parses native text layers with font and layout awareness.
- **OCR Fallback:** Scanned pages ($<40\text{ characters}$) trigger `pytesseract.image_to_string` on high-resolution rasterized page renderings.
- **Policy-Aware Chunking:** Rather than splitting on fixed token counts which split clauses in half, the `PolicyAwareChunker`:
  - Detects regex headings (`Section 4`, `Exclusion 2.1`, `Waiting Periods`).
  - Preserves hierarchical parent context across page boundaries.
  - Retains physical page provenance metadata on every chunk.

---

## 3. Vector Embeddings (`EmbeddingService`)

- **Dimension Enforcement:** Strictly validates that vectors match 768 dimensions without artificial padding or truncation.
- **Providers:**
  - `openai`: `text-embedding-3-small` configured with `dimensions=768`.
  - `gemini`: `text-embedding-004` (768 dimensions).
  - `mock`: Deterministic normalized n-gram token hashing for offline test execution.
- **Batching:** Implements `embed_batch` to optimize network round-trips during chunk ingestion.

---

## 4. Grounded Retrieval & Anti-Hallucination

1. **Policy-Scoped pgvector Retrieval:** Query is converted to vector and executed using `CosineDistance("embedding", query_vec)` directly in PostgreSQL, scoped strictly to `document__policy=policy`.
2. **Evidence Sufficiency Check:** If no chunks surpass the relevance threshold ($\ge 0.2$), the system does not call the LLM and instead immediately returns:
   > *"I couldn't find enough information about this in your policy document."*
3. **Prompt Guardrails:** Instructs LLM to act as a strict extraction engine without speculating or offering unsolicited medical or financial advice.
4. **Independent `CitationVerifier` Layer:**
   - Every citation must match an authentic `DocumentChunk` and `DocumentPage` in PostgreSQL.
   - Page numbers are reconciled against physical document records.
   - The returned citation text is pulled **verbatim from the database**, guaranteeing the LLM cannot alter or distort policy phrasing.

