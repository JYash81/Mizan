"""PDF document parser using pypdf with page and resource bounds."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.modules.documents.parsers.base import (
    BaseParser,
    ExtractedDocumentResult,
    ParserError,
    compute_metrics,
)

MAX_PDF_PAGES = 500


class PdfParser(BaseParser):
    def parse(self, filename: str, content: bytes) -> ExtractedDocumentResult:
        try:
            reader = PdfReader(io.BytesIO(content))
        except (PdfReadError, Exception) as e:
            raise ParserError(f"Failed to read PDF '{filename}': {e}") from e

        total_pages = len(reader.pages)
        if total_pages == 0:
            return compute_metrics("", page_count=0)

        pages_to_read = min(total_pages, MAX_PDF_PAGES)
        page_texts: list[str] = []

        for idx in range(pages_to_read):
            try:
                page = reader.pages[idx]
                text = page.extract_text() or ""
                if text.strip():
                    page_texts.append(f"--- Page {idx + 1} ---\n{text.strip()}")
            except Exception as e:
                page_texts.append(f"--- Page {idx + 1} ---\n[Error reading page: {e}]")

        if total_pages > MAX_PDF_PAGES:
            page_texts.append(f"\n[Note: Truncated after {MAX_PDF_PAGES} pages of {total_pages}]")

        full_text = "\n\n".join(page_texts)
        return compute_metrics(
            full_text,
            page_count=total_pages,
            metadata={"parsed_pages": pages_to_read, "total_pages": total_pages},
        )
