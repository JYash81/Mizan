"""End-to-end Retrieval-Augmented Generation (RAG) Service for Mizan.

Coordinates:
1. Gate 1 Human Approval validation (strict fail-closed invariant).
2. Masked document loading from StorageBucket.MASKED_DATASETS.
3. Bounded sliding-window chunking with source offset preservation.
4. Embedding generation via FastEmbed or Mock.
5. Persistent Qdrant vector indexing with tenant isolation.
6. Semantic retrieval, citation context synthesis, and LLM generation.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import DatasetVersion, Document
from app.modules.masking.approval.gate1_service import require_gate1_approval
from app.modules.rag.chunking.chunker import chunk_document_text
from app.modules.rag.embeddings.base import EmbeddingProvider
from app.modules.rag.providers.base import LLMProvider, LLMResponse
from app.modules.rag.vector_store.base import VectorRecord, VectorStoreProvider
from app.modules.storage import StorageBucket, StorageProvider

logger = logging.getLogger(__name__)


def get_workspace_collection_name(workspace_id: str) -> str:
    """Format sanitized Qdrant collection name for a workspace."""
    clean_id = workspace_id.replace("-", "_")
    return f"mizan_ws_{clean_id}"


def index_approved_dataset_version(
    db: Session,
    workspace_id: str,
    dataset_version_id: str,
    vector_store: VectorStoreProvider,
    embedding_provider: EmbeddingProvider,
    storage: StorageProvider,
    chunk_size_chars: int = 500,
    chunk_overlap_chars: int = 100,
) -> dict[str, Any]:
    """Index an approved masked dataset version into the workspace vector store.

    INVARIANT: Strictly enforces Gate 1 human approval before indexing.
    Only approved masked text from StorageBucket.MASKED_DATASETS is vectorized.
    """
    # 1. Gate 1 Approval Invariant Check (Fails closed with HTTP 403 if unapproved)
    approval = require_gate1_approval(
        db=db,
        workspace_id=workspace_id,
        dataset_version_id=dataset_version_id,
        storage=storage,
    )

    version = db.execute(
        select(DatasetVersion).where(DatasetVersion.id == dataset_version_id)
    ).scalar_one_or_none()
    if not version:
        raise ValueError(f"DatasetVersion {dataset_version_id} not found.")

    documents = (
        db.execute(select(Document).where(Document.dataset_version_id == version.id))
        .scalars()
        .all()
    )

    collection_name = get_workspace_collection_name(workspace_id)
    vector_dim = embedding_provider.get_dimension()
    vector_store.create_collection(collection_name=collection_name, dimension=vector_dim)

    total_chunks_indexed = 0
    total_docs_indexed = 0

    for doc in documents:
        # Load masked text from MASKED_DATASETS using the approved masking run ID
        masked_key = f"runs/{approval.masking_run_id}/docs/{doc.id}.masked.txt"
        masked_text = ""
        try:
            data, _ = storage.get_object(StorageBucket.MASKED_DATASETS, masked_key)
            masked_text = data.decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning(
                "Could not load masked text for document %s at %s: %s",
                doc.id,
                masked_key,
                exc,
            )
            continue

        if not masked_text.strip():
            continue

        # Chunk the masked document text
        chunks = chunk_document_text(
            text=masked_text,
            document_id=doc.id,
            dataset_version_id=version.id,
            chunk_size_chars=chunk_size_chars,
            chunk_overlap_chars=chunk_overlap_chars,
            metadata={"document_name": doc.name, "approval_id": approval.id},
        )

        if not chunks:
            continue

        # Generate embeddings
        chunk_texts = [c.text for c in chunks]
        embeddings = embedding_provider.embed_texts(chunk_texts)

        # Prepare vector records with full metadata payload
        records: list[VectorRecord] = []
        for chunk, vec in zip(chunks, embeddings, strict=True):
            records.append(
                VectorRecord(
                    id=chunk.chunk_id,
                    vector=vec,
                    payload={
                        "workspace_id": workspace_id,
                        "dataset_version_id": version.id,
                        "document_id": doc.id,
                        "document_name": doc.name,
                        "chunk_id": chunk.chunk_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "start_char_offset": chunk.start_char_offset,
                        "end_char_offset": chunk.end_char_offset,
                        "char_count": chunk.char_count,
                        "is_masked": True,
                        "approval_id": approval.id,
                    },
                )
            )

        vector_store.upsert_chunks(collection_name=collection_name, records=records)
        total_chunks_indexed += len(records)
        total_docs_indexed += 1

    return {
        "workspace_id": workspace_id,
        "dataset_version_id": version.id,
        "approval_id": approval.id,
        "collection_name": collection_name,
        "documents_indexed": total_docs_indexed,
        "chunks_indexed": total_chunks_indexed,
        "embedding_model": embedding_provider.get_model_info()["model_name"],
    }


def query_rag(
    workspace_id: str,
    query: str,
    dataset_version_id: str | None,
    vector_store: VectorStoreProvider,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
    top_k: int = 4,
    score_threshold: float = 0.2,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """Execute end-to-end RAG query with strict tenant isolation and citation attribution."""
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Query string cannot be empty.")

    collection_name = get_workspace_collection_name(workspace_id)

    # 1. Embed query
    query_vector = embedding_provider.embed_texts([clean_query])[0]

    # 2. Retrieve top-k chunks with tenant and dataset version filters
    retrieved_chunks = vector_store.search_chunks(
        collection_name=collection_name,
        query_vector=query_vector,
        workspace_id=workspace_id,
        dataset_version_id=dataset_version_id,
        top_k=top_k,
        score_threshold=score_threshold,
    )

    # 3. Generate answer using LLM provider with grounded citations
    response: LLMResponse = llm_provider.generate(
        prompt=clean_query,
        system_prompt=system_prompt,
        context_chunks=retrieved_chunks,
    )

    return {
        "query": clean_query,
        "answer": response.text,
        "citations": response.citations,
        "retrieved_chunks": [
            {
                "chunk_id": c.id,
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "score": round(c.score, 4),
                "text": c.text,
                "payload": c.payload,
            }
            for c in retrieved_chunks
        ],
        "metrics": {
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "latency_ms": response.latency_ms,
            "cost_cents": response.cost_cents,
        },
        "provider": {
            "name": response.provider_name,
            "model": response.model_name,
        },
    }
