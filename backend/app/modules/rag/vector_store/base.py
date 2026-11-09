"""Base interfaces and data structures for Vector Store providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    """A vector embedding with unique ID and rich metadata payload."""

    id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoredChunk:
    """A retrieved chunk with similarity score and metadata."""

    id: str
    score: float
    text: str
    document_id: str
    chunk_index: int
    payload: dict[str, Any] = field(default_factory=dict)


class VectorStoreProvider(ABC):
    """Abstract interface for all Mizan vector database backends."""

    @abstractmethod
    def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a collection if it does not already exist."""

    @abstractmethod
    def upsert_chunks(self, collection_name: str, records: list[VectorRecord]) -> None:
        """Insert or update vector records."""

    @abstractmethod
    def search_chunks(
        self,
        collection_name: str,
        query_vector: list[float],
        workspace_id: str,
        dataset_version_id: str | None = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[ScoredChunk]:
        """Query vectors with mandatory tenant and dataset version isolation filters."""

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Drop a collection and all associated vectors."""

    @abstractmethod
    def count_vectors(self, collection_name: str, workspace_id: str) -> int:
        """Count vectors belonging to a workspace in the specified collection."""

    @abstractmethod
    def close(self) -> None:
        """Safely release storage locks and resources."""
