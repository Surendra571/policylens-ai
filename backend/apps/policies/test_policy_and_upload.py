from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.policies.models import Policy

User = get_user_model()


@pytest.mark.django_db
class TestPolicyManagementAndUpload:
    """Test suite for Policy management CRUD and secure PDF upload pipeline."""

    def setup_method(self):
        self.client_a = APIClient()
        self.client_b = APIClient()

        self.user_a = User.objects.create_user(
            username="user_alpha",
            email="alpha@policylens.ai",
            password="Password123!",
        )
        self.user_b = User.objects.create_user(
            username="user_beta",
            email="beta@policylens.ai",
            password="Password123!",
        )

        self.client_a.force_authenticate(user=self.user_a)
        self.client_b.force_authenticate(user=self.user_b)

        self.policy_a = Policy.objects.create(
            user=self.user_a,
            name="Star Comprehensive Health",
            provider="Star Health",
            policy_type=Policy.PolicyType.FAMILY_FLOATER,
        )
        self.policy_b = Policy.objects.create(
            user=self.user_b,
            name="Care Advantage",
            provider="Care Health",
            policy_type=Policy.PolicyType.INDIVIDUAL,
        )

    def _create_valid_pdf_file(self, filename="policy.pdf", content=b"%PDF-1.4 sample content"):
        return SimpleUploadedFile(
            name=filename,
            content=content,
            content_type="application/pdf",
        )

    # 1. Policy CRUD Tests
    def test_create_policy_authenticated(self):
        """Authenticated user can create a new policy."""
        payload = {
            "name": "Niva Bupa ReAssure 2.0",
            "provider": "Niva Bupa",
            "policy_type": "INDIVIDUAL",
        }
        response = self.client_a.post("/api/v1/policies/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Niva Bupa ReAssure 2.0"
        assert response.data["provider"] == "Niva Bupa"
        assert response.data["status"] == Policy.Status.PENDING

    def test_list_policies_only_returns_own(self):
        """GET /api/v1/policies/ returns only policies of the authenticated user."""
        response = self.client_a.get("/api/v1/policies/")
        assert response.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in response.data["results"]]
        assert str(self.policy_a.id) in ids
        assert str(self.policy_b.id) not in ids

    def test_get_policy_detail(self):
        """GET /api/v1/policies/{id}/ returns policy details for owner."""
        response = self.client_a.get(f"/api/v1/policies/{self.policy_a.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Star Comprehensive Health"

    def test_delete_policy_authorized(self):
        """Owner can delete their own policy returning 204."""
        response = self.client_a.delete(f"/api/v1/policies/{self.policy_a.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Policy.objects.filter(id=self.policy_a.id).exists()

    def test_delete_policy_cross_user_forbidden(self):
        """User A attempting to delete User B's policy receives 404."""
        response = self.client_a.delete(f"/api/v1/policies/{self.policy_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Policy.objects.filter(id=self.policy_b.id).exists()

    # 2. PDF Upload Tests
    @patch("apps.policies.views.process_document_task.delay")
    def test_upload_valid_pdf(self, mock_delay):
        """Uploading valid PDF creates Document with status UPLOADED and queues Celery task."""
        pdf = self._create_valid_pdf_file("health_policy.pdf", b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>%%EOF")
        response = self.client_a.post(
            f"/api/v1/policies/{self.policy_a.id}/documents/",
            {"file": pdf},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        doc_data = response.data["document"]
        assert doc_data["original_filename"] == "health_policy.pdf"
        assert doc_data["processing_status"] == Document.ProcessingStatus.UPLOADED
        assert doc_data["file_size"] > 0

        # Verify Celery async task was queued with the document ID
        mock_delay.assert_called_once()
        assert Document.objects.filter(id=doc_data["id"]).exists()

    def test_upload_invalid_file_extension(self):
        """Uploading non-PDF file (.txt) is rejected with 400."""
        text_file = SimpleUploadedFile(
            name="notes.txt",
            content=b"Just plain text",
            content_type="text/plain",
        )
        response = self.client_a.post(
            f"/api/v1/policies/{self.policy_a.id}/documents/",
            {"file": text_file},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in str(response.data).lower()

    def test_upload_fake_pdf_missing_magic_header(self):
        """Uploading a file named .pdf without %PDF signature is rejected."""
        fake_pdf = SimpleUploadedFile(
            name="fake.pdf",
            content=b"Not a real PDF file header",
            content_type="application/pdf",
        )
        response = self.client_a.post(
            f"/api/v1/policies/{self.policy_a.id}/documents/",
            {"file": fake_pdf},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "signature" in str(response.data).lower() or "%pdf" in str(response.data).lower()

    def test_upload_oversized_file(self):
        """Uploading a file exceeding MAX_UPLOAD_SIZE_MB is rejected with 400."""
        with (
            patch("apps.documents.validators.MAX_UPLOAD_SIZE_MB", 1),
            patch("apps.documents.validators.MAX_UPLOAD_SIZE_BYTES", 100),
        ):
                oversized_pdf = SimpleUploadedFile(
                    name="large.pdf",
                    content=b"%PDF-1.4" + b"X" * 200,
                    content_type="application/pdf",
                )
                response = self.client_a.post(
                    f"/api/v1/policies/{self.policy_a.id}/documents/",
                    {"file": oversized_pdf},
                    format="multipart",
                )
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "size" in str(response.data).lower()

    def test_upload_unauthorized_request(self):
        """Unauthenticated upload request returns 401."""
        anon_client = APIClient()
        pdf = self._create_valid_pdf_file()
        response = anon_client.post(
            f"/api/v1/policies/{self.policy_a.id}/documents/",
            {"file": pdf},
            format="multipart",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_cross_user_policy_prevented(self):
        """User A cannot upload documents to User B's policy (returns 404)."""
        pdf = self._create_valid_pdf_file()
        response = self.client_a.post(
            f"/api/v1/policies/{self.policy_b.id}/documents/",
            {"file": pdf},
            format="multipart",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.policies.views.process_document_task.delay")
    def test_duplicate_document_handling(self, mock_delay):
        """Uploading the exact same PDF to the same policy is detected and rejected as duplicate."""
        content = b"%PDF-1.4 exact duplicate test content"
        pdf1 = self._create_valid_pdf_file("doc.pdf", content)
        res1 = self.client_a.post(
            f"/api/v1/policies/{self.policy_a.id}/documents/",
            {"file": pdf1},
            format="multipart",
        )
        assert res1.status_code == status.HTTP_201_CREATED

        # Try uploading identical document again to same policy
        pdf2 = self._create_valid_pdf_file("doc_copy.pdf", content)
        res2 = self.client_a.post(
            f"/api/v1/policies/{self.policy_a.id}/documents/",
            {"file": pdf2},
            format="multipart",
        )
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert "duplicate" in str(res2.data).lower() or "already been uploaded" in str(res2.data).lower()
