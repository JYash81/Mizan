"""Local Ollama LLM provider adapter for CPU/GPU local execution."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.modules.rag.cost_policy import enforce_cost_policy
from app.modules.rag.providers.base import LLMProvider, LLMResponse, ProviderStatus
from app.modules.rag.vector_store.base import ScoredChunk

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Free, local, sovereign provider connecting to a local Ollama daemon via REST API."""

    def __init__(self, base_url: str | None = None, model_name: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model_name = model_name or settings.ollama_model

    def check_availability(self) -> ProviderStatus:
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models_data = res.json().get("models", [])
                    available_names = [m.get("name") for m in models_data]
                    return ProviderStatus(
                        provider_name="ollama",
                        is_available=True,
                        is_free=True,
                        status_message=f"Ollama running with {len(available_names)} models installed.",
                        cost_per_million_input_cents=0.0,
                        cost_per_million_output_cents=0.0,
                    )
        except Exception as exc:
            logger.debug("Ollama availability check failed: %s", exc)

        return ProviderStatus(
            provider_name="ollama",
            is_available=False,
            is_free=True,
            status_message="Ollama daemon is not reachable at " + self.base_url,
            cost_per_million_input_cents=0.0,
            cost_per_million_output_cents=0.0,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context_chunks: list[ScoredChunk] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        enforce_cost_policy("ollama", operation_type="inference")
        start_time = time.perf_counter()

        # Build context if provided
        context_str = ""
        citations: list[dict[str, Any]] = []
        if context_chunks:
            snippets = []
            for c in context_chunks:
                marker = f"[Doc: {c.document_id}, Chunk: {c.chunk_index}]"
                snippets.append(f"{marker}: {c.text}")
                citations.append(
                    {
                        "citation_marker": marker,
                        "document_id": c.document_id,
                        "chunk_index": c.chunk_index,
                        "score": c.score,
                        "snippet": c.text[:120],
                    }
                )
            context_str = "\nRelevant Business Context:\n" + "\n".join(snippets) + "\n\n"

        full_prompt = f"{context_str}User Question: {prompt}"

        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "system": system_prompt
            or "You are Mizan, a helpful AI assistant. Answer using the provided citations.",
            "stream": False,
            "options": {
                "num_ctx": kwargs.get("num_ctx", 2048),
                "temperature": kwargs.get("temperature", 0.2),
            },
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data = res.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama generation failed: {exc}") from exc

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response_text = data.get("response", "")
        prompt_tokens = data.get("prompt_eval_count", len(full_prompt) // 4)
        completion_tokens = data.get("eval_count", len(response_text) // 4)

        return LLMResponse(
            text=response_text,
            provider_name="ollama",
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            citations=citations,
            cost_cents=0.0,
            finish_reason="stop",
        )
