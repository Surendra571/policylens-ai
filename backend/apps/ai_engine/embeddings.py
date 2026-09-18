import os
import math
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class BaseEmbeddingClient(ABC):
    """Abstract interface for embedding generation providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate an embedding vector for a single string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of strings."""
        pass


class MockEmbeddingClient(BaseEmbeddingClient):
    """
    Deterministic mock embedding client for tests and offline development.
    Generates normalized 768-dimensional vectors using token hashing.
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        tokens = text.lower().split()
        vector = [0.0] * self.dimension

        for i, token in enumerate(tokens):
            for j, char in enumerate(token):
                idx = (hash(token) + (j * 31) + (i * 17)) % self.dimension
                vector[idx] += 1.0

        # L2 normalization
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """OpenAI Embedding Provider using the embeddings REST endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: int = 768,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        batch = self.embed_batch([text])
        return batch[0] if batch else [0.0] * self.dimension

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        if not texts:
            return []

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
            "dimensions": self.dimension,
        }
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        data_items = sorted(data["data"], key=lambda x: x["index"])
        embeddings = [item["embedding"] for item in data_items]

        for emb in embeddings:
            if len(emb) != self.dimension:
                raise ValueError(
                    f"OpenAI returned vector of dimension {len(emb)}, expected {self.dimension}"
                )
        return embeddings


class GeminiEmbeddingClient(BaseEmbeddingClient):
    """Google Gemini Embedding Provider using standard HTTP endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: int = 768,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        if not text:
            return [0.0] * self.dimension

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
        }
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        values = res.json().get("embedding", {}).get("values", [])
        if len(values) != self.dimension:
            raise ValueError(
                f"Gemini returned vector of dimension {len(values)}, expected {self.dimension}"
            )
        return values

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        if not texts:
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={self.api_key}"
        requests_list = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t}]},
            }
            for t in texts
        ]
        payload = {"requests": requests_list}
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        raw_embeddings = res.json().get("embeddings", [])
        results = [e.get("values", []) for e in raw_embeddings]

        for emb in results:
            if len(emb) != self.dimension:
                raise ValueError(
                    f"Gemini returned vector of dimension {len(emb)}, expected {self.dimension}"
                )
        return results


class EmbeddingService:
    """
    Unified high-level Embedding Service.
    Configured through EMBEDDING_PROVIDER environment variable ('mock', 'openai', 'gemini').
    Enforces strict dimension validation (default 768) and supports batching.
    """

    def __init__(
        self,
        dimension: int = 768,
        provider: Optional[str] = None,
        client: Optional[BaseEmbeddingClient] = None,
    ):
        self.dimension = dimension
        if client:
            self.client = client
        else:
            selected_provider = (
                provider or os.getenv("EMBEDDING_PROVIDER") or os.getenv("LLM_PROVIDER") or "mock"
            ).lower()

            if selected_provider == "openai" and os.getenv("OPENAI_API_KEY"):
                self.client = OpenAIEmbeddingClient(dimension=dimension)
            elif selected_provider == "gemini" and os.getenv("GEMINI_API_KEY"):
                self.client = GeminiEmbeddingClient(dimension=dimension)
            else:
                self.client = MockEmbeddingClient(dimension=dimension)

    def get_embedding(self, text: str) -> List[float]:
        """Generate normalized vector for a single text."""
        vec = self.client.embed_text(text)
        self._validate_vector(vec)
        return vec

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized vectors for a batch of texts."""
        if not texts:
            return []
        vectors = self.client.embed_batch(texts)
        for vec in vectors:
            self._validate_vector(vec)
        return vectors

    def _validate_vector(self, vector: List[float]):
        """Ensure vector matches configured dimension without truncation or padding."""
        if len(vector) != self.dimension:
            raise ValueError(
                f"Invalid embedding dimension: got {len(vector)}, expected {self.dimension}."
            )
