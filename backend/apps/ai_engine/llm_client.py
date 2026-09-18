import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(ABC):
    """Abstract base class establishing provider-agnostic interface for LLMs."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate unstructured text from prompt."""

    @abstractmethod
    def generate_structured(self, prompt: str, schema: type[T], **kwargs) -> T:
        """Generate structured data strictly validated against a Pydantic schema."""


class MockLLMClient(BaseLLMClient):
    """Deterministic Mock LLM client for tests and offline development."""

    def __init__(self, mock_response: Any | None = None):
        self.mock_response = mock_response
        self.last_prompt = None

    def generate(self, prompt: str, **kwargs) -> str:
        self.last_prompt = prompt
        if isinstance(self.mock_response, str):
            return self.mock_response
        return "Mock plain-language answer."

    def generate_structured(self, prompt: str, schema: type[T], **kwargs) -> T:
        self.last_prompt = prompt
        if isinstance(self.mock_response, schema):
            return self.mock_response
        elif isinstance(self.mock_response, dict):
            return schema.model_validate(self.mock_response)
        elif isinstance(self.mock_response, str):
            data = json.loads(self.mock_response)
            return schema.model_validate(data)

        # If analyzing policy and no canned mock response was preset, intelligently parse the document prompt
        from .schemas import PolicyAnalysis

        if schema == PolicyAnalysis or issubclass(schema, PolicyAnalysis):
            from .heuristic_parser import parse_insurance_document_text

            parsed = parse_insurance_document_text(prompt)
            return parsed  # type: ignore

        # Default empty model instance
        return schema()


class GeminiLLMClient(BaseLLMClient):
    """Google Gemini LLM provider implementation using standard HTTP REST endpoints."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-pro"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        import requests

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return ""

    def generate_structured(self, prompt: str, schema: type[T], **kwargs) -> T:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        import requests

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
            },
        }
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                raw_json = parts[0].get("text", "{}")
                parsed = json.loads(raw_json)
                return schema.model_validate(parsed)
        return schema()


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM provider implementation using standard Chat Completions HTTP endpoint."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        import requests

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.0),
        }
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"]

    def generate_structured(self, prompt: str, schema: type[T], **kwargs) -> T:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        import requests

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        res = requests.post(url, headers=headers, json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return schema.model_validate(parsed)


def get_llm_client(provider: str | None = None, **kwargs) -> BaseLLMClient:
    """Factory creating configured LLMClient instance based on environment or argument."""
    selected_provider = (provider or os.getenv("LLM_PROVIDER", "mock")).lower()

    if selected_provider == "gemini" and os.getenv("GEMINI_API_KEY"):
        return GeminiLLMClient(**kwargs)
    elif selected_provider == "openai" and os.getenv("OPENAI_API_KEY"):
        return OpenAILLMClient(**kwargs)
    else:
        return MockLLMClient(**kwargs)
