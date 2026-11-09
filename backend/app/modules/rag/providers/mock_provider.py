"""Deterministic Mock LLM Provider for offline development, evaluation, and CI testing."""

from __future__ import annotations

import time
from typing import Any

from app.modules.rag.cost_policy import enforce_cost_policy
from app.modules.rag.providers.base import LLMProvider, LLMResponse, ProviderStatus
from app.modules.rag.vector_store.base import ScoredChunk


class MockLLMProvider(LLMProvider):
    """Zero-cost, deterministic mock generator creating verifiable citation attributions."""

    def __init__(self, model_name: str = "mock-gpt-mizan-v1"):
        self.model_name = model_name

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        context_chunks: list[ScoredChunk] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        enforce_cost_policy("mock", operation_type="inference")
        start_time = time.perf_counter()

        chunks = context_chunks or []
        citations: list[dict[str, Any]] = []

        if chunks:
            # Build grounded response using top chunks
            snippets: list[str] = []
            for i, chunk in enumerate(chunks[:3]):
                snippet_text = chunk.text[:120].strip().replace("\n", " ")
                snippets.append(
                    f'According to document records [Doc: {chunk.document_id}, Chunk: {chunk.chunk_index}]: "{snippet_text}..."'
                )
                citations.append(
                    {
                        "citation_marker": f"[Doc: {chunk.document_id}, Chunk: {chunk.chunk_index}]",
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "score": chunk.score,
                        "snippet": snippet_text,
                    }
                )
            answer_body = " ".join(snippets)
            final_text = (
                f"Based on the approved business documentation, regarding '{prompt}':\n\n"
                f"{answer_body}\n\n"
                "This answer was synthesized from sovereign workshop data with verified citations."
            )
        else:
            final_text = (
                f"Mock response for query: '{prompt}'. "
                "No matching context chunks were retrieved from the vector store."
            )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        prompt_tokens = max(1, len(prompt) // 4)
        completion_tokens = max(1, len(final_text) // 4)

        return LLMResponse(
            text=final_text,
            provider_name="mock",
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            citations=citations,
            cost_cents=0.0,
            finish_reason="stop",
        )

    def check_availability(self) -> ProviderStatus:
        return ProviderStatus(
            provider_name="mock",
            is_available=True,
            is_free=True,
            status_message="Mock provider operational (zero cost, offline)",
            rate_limit_remaining=999999,
            cost_per_million_input_cents=0.0,
            cost_per_million_output_cents=0.0,
        )
