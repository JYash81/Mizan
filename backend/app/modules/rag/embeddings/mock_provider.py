"""Deterministic Mock Embedding Provider for offline, zero-overhead unit testing."""

from __future__ import annotations

import hashlib
import math
from typing import Any

from app.modules.rag.embeddings.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Generates deterministic, normalized 384-dimensional vectors without model downloads."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _hash_to_vector(self, text: str) -> list[float]:
        # Generate deterministic floats from text hash
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw_values: list[float] = []

        # Expand 32 bytes to 384 dimensions deterministically
        for i in range(self.dimension):
            byte_val = digest[i % len(digest)]
            val = math.sin(byte_val * (i + 1) * 0.17)
            raw_values.append(val)

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in raw_values))
        if norm == 0.0:
            return [0.0] * self.dimension
        return [round(x / norm, 6) for x in raw_values]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_info(self) -> dict[str, Any]:
        return {
            "provider": "mock",
            "model_name": "mock-deterministic-384",
            "dimension": self.dimension,
            "license": "Proprietary (Mizan)",
            "runtime": "Pure Python",
            "cost": "$0.00 (Free / Local)",
        }
