"""Unit tests for Qdrant Local Persistent Vector Store and Tenant-Aware Payload Filtering."""

from __future__ import annotations

import tempfile

from app.modules.rag.vector_store.base import VectorRecord
from app.modules.rag.vector_store.qdrant_local import QdrantLocalVectorStore


def test_qdrant_local_store_upsert_and_tenant_isolation() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        store = QdrantLocalVectorStore(path=tmpdir)
        collection = "test_tenant_collection"
        store.create_collection(collection_name=collection, dimension=4)

        # Tenant 1 (Workspace 1) points
        records_ws1 = [
            VectorRecord(
                id="00000000-0000-0000-0000-000000000001",
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={
                    "workspace_id": "ws-alpha",
                    "dataset_version_id": "ver-1",
                    "document_id": "doc-1",
                    "chunk_index": 0,
                    "text": "Alpha confidential handbook",
                },
            ),
            VectorRecord(
                id="00000000-0000-0000-0000-000000000002",
                vector=[0.2, 0.3, 0.4, 0.5],
                payload={
                    "workspace_id": "ws-alpha",
                    "dataset_version_id": "ver-2",
                    "document_id": "doc-2",
                    "chunk_index": 0,
                    "text": "Alpha version 2 updates",
                },
            ),
        ]

        # Tenant 2 (Workspace 2) points
        records_ws2 = [
            VectorRecord(
                id="00000000-0000-0000-0000-000000000003",
                vector=[0.1, 0.2, 0.3, 0.4],  # Similar vector to ws-alpha
                payload={
                    "workspace_id": "ws-beta",
                    "dataset_version_id": "ver-1",
                    "document_id": "doc-3",
                    "chunk_index": 0,
                    "text": "Beta secret operations",
                },
            ),
        ]

        store.upsert_chunks(collection, records_ws1)
        store.upsert_chunks(collection, records_ws2)

        # 1. Verify Tenant Isolation: Alpha queries with its vector
        results_alpha = store.search_chunks(
            collection_name=collection,
            query_vector=[0.1, 0.2, 0.3, 0.4],
            workspace_id="ws-alpha",
            top_k=5,
        )
        assert len(results_alpha) == 2
        for r in results_alpha:
            assert r.payload["workspace_id"] == "ws-alpha"
            assert "Beta" not in r.text

        # 2. Verify Tenant Isolation: Beta queries with identical vector -> NEVER gets Alpha's chunks
        results_beta = store.search_chunks(
            collection_name=collection,
            query_vector=[0.1, 0.2, 0.3, 0.4],
            workspace_id="ws-beta",
            top_k=5,
        )
        assert len(results_beta) == 1
        assert results_beta[0].payload["workspace_id"] == "ws-beta"
        assert "Alpha" not in results_beta[0].text

        # 3. Verify Dataset Version Filtering
        results_ver2 = store.search_chunks(
            collection_name=collection,
            query_vector=[0.1, 0.2, 0.3, 0.4],
            workspace_id="ws-alpha",
            dataset_version_id="ver-2",
            top_k=5,
        )
        assert len(results_ver2) == 1
        assert results_ver2[0].payload["dataset_version_id"] == "ver-2"

        # 4. Count vectors per workspace
        assert store.count_vectors(collection, workspace_id="ws-alpha") == 2
        assert store.count_vectors(collection, workspace_id="ws-beta") == 1

        store.close()


def test_qdrant_in_memory_mode() -> None:
    store = QdrantLocalVectorStore(in_memory=True)
    store.create_collection("mem_coll", dimension=2)
    store.upsert_chunks(
        "mem_coll",
        [
            VectorRecord(
                id="00000000-0000-0000-0000-000000000001",
                vector=[1.0, 0.0],
                payload={"workspace_id": "ws-1", "text": "In-memory test"},
            )
        ],
    )
    res = store.search_chunks("mem_coll", query_vector=[1.0, 0.0], workspace_id="ws-1")
    assert len(res) == 1
    assert res[0].text == "In-memory test"
    store.close()
