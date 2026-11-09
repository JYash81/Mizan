"""Optional experimental Google Gemini Free-Tier provider adapter."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.modules.rag.cost_policy import enforce_cost_policy, notify_quota_exhausted
from app.modules.rag.privacy_policy import (
    DataClassification,
    validate_provider_data_sharing,
)
from app.modules.rag.providers.base import LLMProvider, LLMResponse, ProviderStatus
from app.modules.rag.vector_store.base import ScoredChunk

logger = logging.getLogger(__name__)


class GeminiFreeProvider(LLMProvider):
    """Free-tier Gemini adapter for non-confidential development & synthetic benchmark generation.

    Strictly governed: Never receives confidential business data without explicit customer opt-in.
    Never automatically upgrades to paid billing upon rate limits.
    """

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        self.endpoint_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

    def check_availability(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus(
                provider_name="gemini_free",
                is_available=False,
                is_free=True,
                status_message="GEMINI_API_KEY is not configured.",
                cost_per_million_input_cents=0.0,
                cost_per_million_output_cents=0.0,
            )

        return ProviderStatus(
            provider_name="gemini_free",
            is_available=True,
            is_free=True,
            status_message="Gemini free-tier configured (subject to 15 RPM / 1M TPM free limits).",
            cost_per_million_input_cents=0.0,
            cost_per_million_output_cents=0.0,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context_chunks: list[ScoredChunk] | None = None,
        data_classification: DataClassification = DataClassification.INTERNAL_NON_CONFIDENTIAL,
        is_gate1_approved: bool = True,
        customer_cloud_opt_in: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        enforce_cost_policy("gemini_free", operation_type="inference")
        validate_provider_data_sharing(
            "gemini_free",
            classification=data_classification,
            is_gate1_approved=is_gate1_approved,
            customer_cloud_opt_in=customer_cloud_opt_in,
        )

        if not self.api_key:
            raise RuntimeError("Gemini Free Provider requires GEMINI_API_KEY.")

        start_time = time.perf_counter()

        # Build context
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
            context_str = "\nContext Citations:\n" + "\n".join(snippets) + "\n\n"

        full_prompt = f"{context_str}Question: {prompt}"

        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.2),
                "maxOutputTokens": kwargs.get("max_tokens", 1024),
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(
                    f"{self.endpoint_url}?key={self.api_key}",
                    json=payload,
                )
                if res.status_code == 429:
                    notify_quota_exhausted("gemini_free", retry_after_seconds=60)

                res.raise_for_status()
                data = res.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                notify_quota_exhausted("gemini_free", retry_after_seconds=60)
            raise RuntimeError(f"Gemini API error: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Gemini network error: {exc}") from exc

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        candidates = data.get("candidates", [])
        answer_text = ""
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                answer_text = parts[0].get("text", "")

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", len(full_prompt) // 4)
        completion_tokens = usage.get("candidatesTokenCount", len(answer_text) // 4)

        return LLMResponse(
            text=answer_text,
            provider_name="gemini_free",
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            citations=citations,
            cost_cents=0.0,
            finish_reason="stop",
        )
