"""FastEmbed local CPU embedding provider using ONNX Runtime."""

from __future__ import annotations

import logging
import math
from typing import Any

from app.core.config import get_settings
from app.modules.rag.cost_policy import enforce_cost_policy
from app.modules.rag.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class FastEmbedProvider(EmbeddingProvider):
    """Local, sovereign, free embedding generator running on CPU via FastEmbed + ONNX."""

    def __init__(
        self,
        model_name: str | None = None,
        cache_dir: str | None = None,
    ):
        settings = get_settings()
        self.model_name = model_name or settings.fastembed_model_name
        self.cache_dir = cache_dir or settings.fastembed_cache_dir
        self.dimension = 384
        self._model = None

    def _load_model(self) -> None:
        if self._model is None:
            enforce_cost_policy("fastembed_local", operation_type="embedding")
            from fastembed import TextEmbedding

            logger.info(
                "Loading FastEmbed model '%s' from cache directory '%s'...",
                self.model_name,
                self.cache_dir,
            )
            self._model = TextEmbedding(
                model_name=self.model_name,
                cache_dir=self.cache_dir,
            )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._load_model()
        embeddings_gen = self._model.embed(texts)
        results = []
        for vec in embeddings_gen:
            raw = [float(v) for v in vec]
            norm = math.sqrt(sum(x * x for x in raw))
            if norm > 0.0:
                normalized = [round(x / norm, 6) for x in raw]
            else:
                normalized = raw
            results.append(normalized)
        return results

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_info(self) -> dict[str, Any]:
        return {
            "provider": "fastembed_local",
            "model_name": self.model_name,
            "dimension": self.dimension,
            "license": "Apache-2.0",
            "runtime": "ONNX Runtime (CPU)",
            "languages": "Multilingual (~50 languages including English and Arabic)",
            "cost": "$0.00 (Free / Local)",
        }
