"""DOCX document parser using python-docx."""

import io

from docx import Document as DocxDocument

from app.modules.documents.parsers.base import (
    BaseParser,
    ExtractedDocumentResult,
    ParserError,
    compute_metrics,
)


class DocxParser(BaseParser):
    def parse(self, filename: str, content: bytes) -> ExtractedDocumentResult:
        try:
            doc = DocxDocument(io.BytesIO(content))
        except Exception as e:
            raise ParserError(f"Failed to open DOCX file '{filename}': {e}") from e

        elements: list[str] = []

        # Extract paragraphs
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                elements.append(text)

        # Extract tables
        for table in doc.tables:
            table_lines: list[str] = []
            for row in table.rows:
                row_vals = [cell.text.strip() for cell in row.cells]
                table_lines.append(" | ".join(row_vals))
            if table_lines:
                elements.append("\n".join(table_lines))

        full_text = "\n\n".join(elements)
        return compute_metrics(
            full_text,
            metadata={"paragraph_count": len(doc.paragraphs), "table_count": len(doc.tables)},
        )
