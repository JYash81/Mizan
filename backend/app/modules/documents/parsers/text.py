"""Plain text and markdown parser."""

from app.modules.documents.parsers.base import (
    BaseParser,
    ExtractedDocumentResult,
    ParserError,
    compute_metrics,
)


class TextParser(BaseParser):
    def parse(self, filename: str, content: bytes) -> ExtractedDocumentResult:
        try:
            try:
                decoded = content.decode("utf-8")
            except UnicodeDecodeError:
                decoded = content.decode("latin-1")
        except Exception as e:
            raise ParserError(f"Failed to decode text file '{filename}': {e}") from e

        # Normalize line endings
        normalized = decoded.replace("\r\n", "\n").replace("\r", "\n")
        return compute_metrics(normalized)
