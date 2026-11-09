"""Qdrant Local Persistent Vector Store implementation for Mizan."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import get_settings
from app.modules.rag.vector_store.base import ScoredChunk, VectorRecord, VectorStoreProvider

logger = logging.getLogger(__name__)

_CLIENT_CACHE: dict[str, QdrantClient] = {}


def get_shared_qdrant_client(path: str) -> QdrantClient:
    """Return a shared singleton QdrantClient for a given path to prevent file lock collisions."""
    normalized = str(Path(path).resolve())
    if normalized not in _CLIENT_CACHE:
        _CLIENT_CACHE[normalized] = QdrantClient(path=normalized)
    return _CLIENT_CACHE[normalized]


class QdrantLocalVectorStore(VectorStoreProvider):
    """Local embedded Qdrant vector database running in single-process persistent disk mode.

    Zero Docker, zero cloud subscription, zero external servers.
    """

    def __init__(self, path: str | None = None, in_memory: bool = False):
        self.in_memory = in_memory
        if in_memory:
            self.client = QdrantClient(location=":memory:")
            self.storage_path = ":memory:"
            logger.info("Initialized QdrantLocalVectorStore in-memory.")
        else:
            settings = get_settings()
            actual_path = path or settings.qdrant_path
            Path(actual_path).mkdir(parents=True, exist_ok=True)
            self.storage_path = actual_path
            self.client = get_shared_qdrant_client(actual_path)
            logger.info("Initialized QdrantLocalVectorStore with persistent path: %s", actual_path)

    def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a collection if it does not already exist with Cosine distance."""
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            logger.info(
                "Created Qdrant collection '%s' with dimension %d.",
                collection_name,
                dimension,
            )

    def upsert_chunks(self, collection_name: str, records: list[VectorRecord]) -> None:
        """Insert or update embedded vector records."""
        if not records:
            return

        points = [
            PointStruct(
                id=r.id,
                vector=r.vector,
                payload=r.payload,
            )
            for r in records
        ]
        self.client.upsert(collection_name=collection_name, points=points)
        logger.debug("Upserted %d points into collection '%s'.", len(points), collection_name)

    def search_chunks(
        self,
        collection_name: str,
        query_vector: list[float],
        workspace_id: str,
        dataset_version_id: str | None = None,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[ScoredChunk]:
        """Search vectors with mandatory tenant isolation filter on workspace_id."""
        if not self.client.collection_exists(collection_name):
            return []

        must_conditions: list[Any] = [
            FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
        ]
        if dataset_version_id:
            must_conditions.append(
                FieldCondition(
                    key="dataset_version_id",
                    match=MatchValue(value=dataset_version_id),
                )
            )

        query_filter = Filter(must=must_conditions)

        res = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold if score_threshold > 0.0 else None,
        )

        results: list[ScoredChunk] = []
        for p in res.points:
            payload = p.payload or {}
            results.append(
                ScoredChunk(
                    id=str(p.id),
                    score=float(p.score) if p.score is not None else 0.0,
                    text=str(payload.get("text", "")),
                    document_id=str(payload.get("document_id", "")),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    payload=payload,
                )
            )
        return results

    def delete_collection(self, collection_name: str) -> None:
        """Drop collection and all points."""
        if self.client.collection_exists(collection_name):
            self.client.delete_collection(collection_name=collection_name)
            logger.info("Deleted Qdrant collection '%s'.", collection_name)

    def count_vectors(self, collection_name: str, workspace_id: str) -> int:
        """Count vectors belonging to a workspace."""
        if not self.client.collection_exists(collection_name):
            return 0
        q_filter = Filter(
            must=[FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))]
        )
        return self.client.count(collection_name=collection_name, count_filter=q_filter).count

    def close(self) -> None:
        """Explicitly close client to release file locks on Windows."""
        try:
            self.client.close()
        except Exception as exc:
            logger.debug("Error while closing QdrantClient: %s", exc)
