"""Unit tests for sliding window Document Chunker and Embedding Providers."""

from __future__ import annotations

import math

from app.modules.rag.chunking.chunker import chunk_document_text
from app.modules.rag.embeddings.fastembed_provider import FastEmbedProvider
from app.modules.rag.embeddings.mock_provider import MockEmbeddingProvider


def test_chunk_document_text_sliding_window_and_offsets() -> None:
    text = (
        "Mizan enables enterprises to experiment with sovereign AI.\n"
        "All business documents remain inside the local workshop boundary.\n"
        "Personal data is masked before external testing.\n"
        "Gate 1 ensures human sign-off on all masked samples."
    )

    chunks = chunk_document_text(
        text=text,
        document_id="doc-123",
        dataset_version_id="ver-456",
        chunk_size_chars=80,
        chunk_overlap_chars=20,
    )

    assert len(chunks) >= 3
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.document_id == "doc-123"
        assert c.dataset_version_id == "ver-456"
        assert c.start_char_offset >= 0
        assert c.end_char_offset <= len(text)
        assert c.start_char_offset < c.end_char_offset
        # Exact character slice check
        assert c.text == text[c.start_char_offset : c.end_char_offset].strip()


def test_chunk_document_empty_text() -> None:
    chunks = chunk_document_text(
        text="",
        document_id="doc-empty",
        dataset_version_id="ver-1",
    )
    assert chunks == []


def test_mock_embedding_provider_dimension_and_determinism() -> None:
    provider = MockEmbeddingProvider(dimension=384)
    assert provider.get_dimension() == 384

    texts = ["Mizan AI Platform", "Sovereign Workshop Data"]
    vecs = provider.embed_texts(texts)

    assert len(vecs) == 2
    assert len(vecs[0]) == 384
    assert len(vecs[1]) == 384

    # Length of unit vector must be approximately 1.0
    norm_0 = math.sqrt(sum(x * x for x in vecs[0]))
    assert round(norm_0, 4) == 1.0

    # Determinism: identical text produces identical vector
    repeat_vecs = provider.embed_texts(["Mizan AI Platform"])
    assert vecs[0] == repeat_vecs[0]


def test_fastembed_multilingual_english_arabic() -> None:
    provider = FastEmbedProvider()
    assert provider.get_dimension() == 384
    info = provider.get_model_info()
    assert info["provider"] == "fastembed_local"
    assert info["license"] == "Apache-2.0"

    samples = [
        "Welcome to Mizan AI",
        "مرحبا بكم في منصة ميزان للذكاء الاصطناعي",
        "Sovereign data protection in the UAE (دولة الإمارات العربية المتحدة)",
    ]
    vectors = provider.embed_texts(samples)

    assert len(vectors) == 3
    for vec in vectors:
        assert len(vec) == 384
        # Normalized vector check
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 0.05
