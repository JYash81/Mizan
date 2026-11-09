"""Unit tests for Mizan LLM Inference Providers and Registry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.modules.rag.cost_policy import FreeQuotaExhaustedError, PaidProviderRejectedError
from app.modules.rag.privacy_policy import (
    DataClassification,
    PrivacyPolicyViolationError,
)
from app.modules.rag.providers.gemini_free_provider import GeminiFreeProvider
from app.modules.rag.providers.mock_provider import MockLLMProvider
from app.modules.rag.providers.ollama_provider import OllamaProvider
from app.modules.rag.providers.registry import (
    get_llm_provider,
    list_registered_providers,
)
from app.modules.rag.vector_store.base import ScoredChunk


def test_mock_llm_provider_generation_and_citations():
    """Verify MockLLMProvider generates deterministic text and citations with zero cost."""
    provider = MockLLMProvider(model_name="mock-test-v1")
    status = provider.check_availability()
    assert status.is_available is True
    assert status.is_free is True
    assert status.cost_per_million_input_cents == 0.0

    # 1. No context chunks
    res_no_ctx = provider.generate(prompt="What is Mizan?")
    assert "Mock response for query: 'What is Mizan?'" in res_no_ctx.text
    assert res_no_ctx.provider_name == "mock"
    assert res_no_ctx.cost_cents == 0.0
    assert len(res_no_ctx.citations) == 0

    # 2. With context chunks
    sample_chunks = [
        ScoredChunk(
            id="c1",
            score=0.92,
            text="Mizan is an enterprise AI experimentation and evaluation platform.",
            document_id="doc-123",
            chunk_index=0,
            payload={"workspace_id": "ws-1", "dataset_version_id": "ver-1"},
        ),
        ScoredChunk(
            id="c2",
            score=0.88,
            text="All business data is masked and approved at Gate 1 before experimentation.",
            document_id="doc-123",
            chunk_index=1,
            payload={"workspace_id": "ws-1", "dataset_version_id": "ver-1"},
        ),
    ]

    res_ctx = provider.generate(prompt="Explain Gate 1", context_chunks=sample_chunks)
    assert "[Doc: doc-123, Chunk: 0]" in res_ctx.text
    assert "[Doc: doc-123, Chunk: 1]" in res_ctx.text
    assert len(res_ctx.citations) == 2
    assert res_ctx.citations[0]["document_id"] == "doc-123"
    assert res_ctx.citations[0]["chunk_index"] == 0
    assert res_ctx.citations[0]["score"] == 0.92
    assert res_ctx.cost_cents == 0.0
    assert res_ctx.latency_ms >= 0


def test_ollama_provider_handling():
    """Verify OllamaProvider behaves gracefully when daemon is unreachable and handles responses."""
    # When daemon is unreachable
    provider = OllamaProvider(base_url="http://127.0.0.1:9999", model_name="llama3.2:1b")
    status = provider.check_availability()
    assert status.is_available is False
    assert status.is_free is True
    assert "not reachable" in status.status_message

    # Test generation with mocked httpx
    sample_chunks = [
        ScoredChunk(
            id="c1",
            score=0.95,
            text="Ollama runs entirely locally on CPU or local GPU.",
            document_id="doc-99",
            chunk_index=0,
            payload={"workspace_id": "ws-1", "dataset_version_id": "ver-1"},
        )
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "Local LLM output based on Ollama.",
        "prompt_eval_count": 25,
        "eval_count": 15,
    }

    with patch("httpx.Client.post", return_value=mock_response):
        res = provider.generate(prompt="Where does Ollama run?", context_chunks=sample_chunks)
        assert res.text == "Local LLM output based on Ollama."
        assert res.provider_name == "ollama"
        assert res.cost_cents == 0.0
        assert res.prompt_tokens == 25
        assert res.completion_tokens == 15
        assert len(res.citations) == 1
        assert res.citations[0]["citation_marker"] == "[Doc: doc-99, Chunk: 0]"


def test_gemini_free_provider_privacy_and_quota():
    """Verify GeminiFreeProvider privacy constraints and hard quota exhaustion stop."""
    provider = GeminiFreeProvider(api_key="test-api-key", model_name="gemini-1.5-flash")

    # 1. Privacy enforcement: cannot share confidential data without opt-in
    with pytest.raises(PrivacyPolicyViolationError):
        provider.generate(
            prompt="Process confidential report",
            data_classification=DataClassification.CONFIDENTIAL_CUSTOMER,
            customer_cloud_opt_in=False,
            is_gate1_approved=True,
        )

    # 2. Availability check
    status = provider.check_availability()
    assert status.is_available is True
    assert status.is_free is True

    # 3. Successful free generation
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Gemini free tier analysis."}],
                    "role": "model",
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 20,
            "candidatesTokenCount": 10,
        },
    }

    with patch("httpx.Client.post", return_value=mock_success):
        res = provider.generate(
            prompt="Analyze public overview",
            data_classification=DataClassification.PUBLIC,
            customer_cloud_opt_in=True,
            is_gate1_approved=True,
        )
        assert res.text == "Gemini free tier analysis."
        assert res.provider_name == "gemini_free"
        assert res.cost_cents == 0.0
        assert res.prompt_tokens == 20
        assert res.completion_tokens == 10

    # 4. HTTP 429 Quota Exhaustion -> Hard stop with FreeQuotaExhaustedError (NEVER auto-upgrades)
    mock_429 = MagicMock()
    mock_429.status_code = 429

    with patch("httpx.Client.post", return_value=mock_429):
        with pytest.raises(FreeQuotaExhaustedError) as exc_info:
            provider.generate(
                prompt="Exhausted quota query",
                data_classification=DataClassification.PUBLIC,
                customer_cloud_opt_in=True,
                is_gate1_approved=True,
            )
        assert "Free quota exhausted for provider 'gemini_free'" in str(exc_info.value)


def test_provider_registry_and_cost_rejection():
    """Verify registry resolves free providers and rejects paid providers under cost policy."""
    # Free providers resolve
    mock_p = get_llm_provider("mock")
    assert isinstance(mock_p, MockLLMProvider)

    ollama_p = get_llm_provider("ollama")
    assert isinstance(ollama_p, OllamaProvider)

    gemini_p = get_llm_provider("gemini_free", api_key="dummy-key")
    assert isinstance(gemini_p, GeminiFreeProvider)

    # Paid providers strictly rejected
    with pytest.raises(PaidProviderRejectedError):
        get_llm_provider("openai")

    with pytest.raises(PaidProviderRejectedError):
        get_llm_provider("anthropic")

    # List registered providers
    statuses = list_registered_providers()
    assert len(statuses) == 3
    provider_names = {s.provider_name for s in statuses}
    assert provider_names == {"mock", "ollama", "gemini_free"}
    assert all(s.is_free is True for s in statuses)
