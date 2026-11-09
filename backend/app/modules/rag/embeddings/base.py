"""Base interface for embedding providers in Mizan."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for input strings."""

    @abstractmethod
    def get_dimension(self) -> int:
        """Return dimensionality of the embedding vectors."""

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Return model metadata, license, and version."""
