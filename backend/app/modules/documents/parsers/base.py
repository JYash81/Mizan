"""Base classes and types for Mizan document parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ParserError(Exception):
    """Raised when document parsing fails."""


@dataclass(frozen=True)
class ExtractedDocumentResult:
    text: str
    sample: str
    char_count: int
    word_count: int
    page_count: int | None = None
    metadata: dict = field(default_factory=dict)


def compute_metrics(
    text: str, page_count: int | None = None, metadata: dict | None = None
) -> ExtractedDocumentResult:
    cleaned = text.strip()
    char_count = len(cleaned)
    word_count = len(cleaned.split()) if cleaned else 0
    sample = cleaned[:1000]
    return ExtractedDocumentResult(
        text=cleaned,
        sample=sample,
        char_count=char_count,
        word_count=word_count,
        page_count=page_count,
        metadata=metadata or {},
    )


class BaseParser(ABC):
    @abstractmethod
    def parse(self, filename: str, content: bytes) -> ExtractedDocumentResult:
        """Parse raw binary bytes and return normalized extracted text and metrics."""
