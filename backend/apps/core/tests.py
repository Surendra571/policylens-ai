import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.ai_engine.embeddings import (
    EmbeddingService,
    MockEmbeddingClient,
)


@pytest.mark.django_db
def test_health_check_endpoint():
    client = APIClient()
    url = reverse("health-check")
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "healthy"
    assert "services" in response.data
    assert response.data["services"]["database"] == "healthy"
    assert response.data["services"]["redis"] == "healthy"


def test_celery_configuration():
    from config.celery import app as celery_app
    assert celery_app.main == "policylens"


def test_app_urls_accessible():
    client = APIClient()
    for app in ["accounts", "policies", "documents", "clauses", "chat", "ai"]:
        url = f"/api/v1/{app}/status/"
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK


def test_embedding_service_dimension_and_normalization():
    service = EmbeddingService(dimension=768)
    vec = service.get_embedding("Health insurance pre-existing disease waiting period")
    assert len(vec) == 768
    # Test L2 normalization
    norm = sum(x * x for x in vec) ** 0.5
    assert pytest.approx(norm, rel=1e-3) == 1.0


def test_embedding_service_batching():
    service = EmbeddingService(dimension=768)
    texts = [
        "Inpatient hospitalisation coverage",
        "Maternity benefit with 24 months waiting period",
        "Day care procedures listed in policy schedule",
    ]
    vectors = service.get_embeddings(texts)
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 768


def test_embedding_invalid_dimension_rejection():
    class BrokenClient(MockEmbeddingClient):
        def embed_text(self, text):
            return [0.1] * 512

    service = EmbeddingService(dimension=768, client=BrokenClient(dimension=512))
    with pytest.raises(ValueError, match="Invalid embedding dimension"):
        service.get_embedding("Test text")


@pytest.mark.django_db
def test_throttling_rates_configured():
    from apps.core.throttles import DocumentUploadThrottle, PolicyAnalysisThrottle, PolicyChatThrottle
    assert DocumentUploadThrottle.scope == "document_upload"
    assert PolicyAnalysisThrottle.scope == "policy_analysis"
    assert PolicyChatThrottle.scope == "policy_chat"
