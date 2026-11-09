"""Bounded, offset-preserving sliding window document chunker for Mizan RAG."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentChunk:
    """A granular chunk of extracted text with traceable source document offsets."""

    chunk_id: str
    document_id: str
    dataset_version_id: str
    chunk_index: int
    text: str
    start_char_offset: int
    end_char_offset: int
    char_count: int
    estimated_tokens: int
    metadata: dict[str, Any] = field(default_factory=dict)


def chunk_document_text(
    text: str,
    document_id: str,
    dataset_version_id: str,
    chunk_size_chars: int = 500,
    chunk_overlap_chars: int = 100,
    metadata: dict[str, Any] | None = None,
) -> list[DocumentChunk]:
    """Segment document text into sliding-window chunks with source offset tracking.

    Ensures:
    - Bounded character count
    - Non-negative, strictly monotonically increasing chunk indexes
    - Exact character slice coordinates [start_char_offset, end_char_offset)
    - Metadata propagation for tenant-aware vector indexing
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    text_len = len(clean_text)
    effective_overlap = min(chunk_overlap_chars, max(0, chunk_size_chars - 1))
    step = max(1, chunk_size_chars - effective_overlap)

    chunks: list[DocumentChunk] = []
    start = 0
    chunk_idx = 0
    meta = metadata or {}

    while start < text_len:
        end = min(start + chunk_size_chars, text_len)

        # Attempt natural boundary snapping if not at the absolute end
        if end < text_len:
            # Look backwards up to 50 chars for a newline or sentence break
            lookback = clean_text[max(start, end - 50) : end]
            last_break = max(lookback.rfind("\n"), lookback.rfind(". "), lookback.rfind(" "))
            if last_break != -1:
                # Snap end to the natural break
                end = max(start + 1, end - 50 + last_break + 1)

        chunk_str = clean_text[start:end].strip()

        if chunk_str:
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                dataset_version_id=dataset_version_id,
                chunk_index=chunk_idx,
                text=chunk_str,
                start_char_offset=start,
                end_char_offset=end,
                char_count=len(chunk_str),
                estimated_tokens=max(1, len(chunk_str) // 4),
                metadata={
                    **meta,
                    "document_id": document_id,
                    "dataset_version_id": dataset_version_id,
                    "chunk_index": chunk_idx,
                },
            )
            chunks.append(chunk)
            chunk_idx += 1

        if end >= text_len:
            break

        start += step

    return chunks
