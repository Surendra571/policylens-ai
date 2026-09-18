# PolicyLens AI Documentation

Welcome to the PolicyLens AI documentation directory.

## System Architecture

PolicyLens AI is structured as a modular monolith:

- **Backend:** Django 5, Django REST Framework, Celery, PostgreSQL with pgvector, Redis.
- **Frontend:** React 19 / Vite, TypeScript, Tailwind CSS, TanStack Query.
- **Worker & OCR Pipeline:** Celery async tasks with PyMuPDF and Tesseract fallback.
- **AI & RAG Engine:** Grounded retrieval-augmented generation with strict page/clause citations.

## Documentation Index

- [Architecture Overview](./architecture.md)
- [API Specifications](./api.md)
- [Deployment Guide](./deployment.md)

