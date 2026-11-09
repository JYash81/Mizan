"""Parser dispatcher resolving file types to bounded parser implementations."""

from app.models.dataset import DocumentFileType
from app.modules.documents.parsers.base import BaseParser, ExtractedDocumentResult, ParserError
from app.modules.documents.parsers.docx_parser import DocxParser
from app.modules.documents.parsers.image import ImageParser
from app.modules.documents.parsers.json_parser import JsonParser
from app.modules.documents.parsers.pdf import PdfParser
from app.modules.documents.parsers.tabular import CsvParser, XlsxParser
from app.modules.documents.parsers.text import TextParser

_PARSERS: dict[DocumentFileType, BaseParser] = {
    DocumentFileType.TXT: TextParser(),
    DocumentFileType.CSV: CsvParser(),
    DocumentFileType.XLSX: XlsxParser(),
    DocumentFileType.JSON: JsonParser(),
    DocumentFileType.JSONL: JsonParser(),
    DocumentFileType.PDF: PdfParser(),
    DocumentFileType.DOCX: DocxParser(),
    DocumentFileType.IMAGE: ImageParser(),
}


def get_parser(file_type: DocumentFileType | str) -> BaseParser:
    target = DocumentFileType(file_type) if isinstance(file_type, str) else file_type
    parser = _PARSERS.get(target)
    if not parser:
        raise ParserError(f"No registered parser for file type: {target}")
    return parser


def parse_document(
    file_type: DocumentFileType | str, filename: str, content: bytes
) -> ExtractedDocumentResult:
    parser = get_parser(file_type)
    return parser.parse(filename, content)
