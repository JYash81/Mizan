"""Document parsers package."""

from app.modules.documents.parsers.base import BaseParser, ExtractedDocumentResult, ParserError
from app.modules.documents.parsers.dispatcher import get_parser, parse_document

__all__ = [
    "BaseParser",
    "ExtractedDocumentResult",
    "ParserError",
    "get_parser",
    "parse_document",
]
