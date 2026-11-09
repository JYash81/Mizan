"""Tests for file validation, decompression-bomb defenses, and magic bytes."""

import io
import zipfile

import pytest
from docx import Document as DocxDoc
from openpyxl import Workbook
from PIL import Image as PilImg
from pypdf import PdfWriter

from app.models.dataset import DocumentFileType
from app.modules.documents.parsers import parse_document
from app.modules.documents.services.file_validator import (
    DecompressionBombDetectedError,
    FileFormatUnsupportedError,
    FileSizeLimitExceededError,
    FileValidationError,
    sanitize_filename,
    validate_file_upload,
)


def test_sanitize_filename():
    assert sanitize_filename("normal_doc.pdf") == "normal_doc.pdf"
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\secret.docx") == "secret.docx"
    assert sanitize_filename("bad:name*with?chars.txt") == "bad_name_with_chars.txt"
    assert sanitize_filename("...   ") == "unnamed_document.bin"


def test_validate_empty_file():
    with pytest.raises(FileValidationError, match="empty"):
        validate_file_upload("empty.txt", b"")


def test_validate_file_size_limit():
    large_payload = b"x" * 1024
    with pytest.raises(FileSizeLimitExceededError):
        validate_file_upload("test.txt", large_payload, max_size_bytes=512)


def test_validate_valid_text_and_csv():
    txt = validate_file_upload("notes.txt", b"Hello Mizan Notes")
    assert txt.file_type == "TXT"
    assert txt.mime_type == "text/plain"

    csv_data = b"col1,col2\nval1,val2\n"
    csv = validate_file_upload("data.csv", csv_data)
    assert csv.file_type == "CSV"
    assert csv.mime_type == "text/csv"


def test_validate_magic_byte_mismatch():
    # PDF extension but plain text payload
    with pytest.raises(FileFormatUnsupportedError, match="lacks %PDF magic header"):
        validate_file_upload("fake.pdf", b"This is just text not a real pdf")

    # PNG extension but corrupt header
    with pytest.raises(FileFormatUnsupportedError, match="Invalid PNG magic header"):
        validate_file_upload("fake.png", b"not a png image")


def test_validate_valid_pdf_magic():
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    pdf = validate_file_upload("contract.pdf", pdf_bytes)
    assert pdf.file_type == "PDF"
    assert pdf.mime_type == "application/pdf"
    assert len(pdf.sha256) == 64


def test_validate_zip_bomb_rejection():
    # Create an artificial zip with massive repetition / extreme ratio
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # 10 MB of zeros compresses into ~10 KB (ratio ~ 1000:1)
        z.writestr("word/document.xml", b"\x00" * (10 * 1024 * 1024))

    zip_bomb_bytes = buf.getvalue()

    with pytest.raises(DecompressionBombDetectedError, match="exceeds limit"):
        validate_file_upload("bomb.docx", zip_bomb_bytes)


def test_validate_nested_archive_rejection():
    # DOCX containing a nested zip
    inner_buf = io.BytesIO()
    with zipfile.ZipFile(inner_buf, "w") as iz:
        iz.writestr("inner.txt", b"inner")

    outer_buf = io.BytesIO()
    with zipfile.ZipFile(outer_buf, "w") as oz:
        oz.writestr("word/document.xml", b"<xml></xml>")
        oz.writestr("word/nested.zip", inner_buf.getvalue())

    with pytest.raises(DecompressionBombDetectedError, match="Nested archive forbidden"):
        validate_file_upload("nested.docx", outer_buf.getvalue())


def test_parse_text_and_markdown():
    res = parse_document(DocumentFileType.TXT, "readme.md", b"# Title\nThis is a sample document.")
    assert "Title" in res.text
    assert res.word_count == 7
    assert res.char_count > 0


def test_parse_csv():
    csv_bytes = b"col1,col2\nval1,val2\nval3,val4\n"
    res = parse_document(DocumentFileType.CSV, "test.csv", csv_bytes)
    assert "col1 | col2" in res.text
    assert "val3 | val4" in res.text
    assert res.metadata.get("row_count") == 3


def test_parse_json_and_jsonl():
    json_bytes = b'{"name": "Mizan", "modules": ["storage", "ingestion"]}'
    res = parse_document(DocumentFileType.JSON, "data.json", json_bytes)
    assert '"name": "Mizan"' in res.text

    jsonl_bytes = b'{"event": "start"}\n{"event": "finish"}\n'
    res_l = parse_document(DocumentFileType.JSONL, "events.jsonl", jsonl_bytes)
    assert "Record 1" in res_l.text
    assert "Record 2" in res_l.text
    assert res_l.metadata.get("record_count") == 2


def test_parse_docx():
    doc = DocxDoc()
    doc.add_heading("Architecture Overview", level=1)
    doc.add_paragraph("This is the workshop data plane.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Header 1"
    table.rows[0].cells[1].text = "Header 2"
    table.rows[1].cells[0].text = "Cell A"
    table.rows[1].cells[1].text = "Cell B"

    buf = io.BytesIO()
    doc.save(buf)

    res = parse_document(DocumentFileType.DOCX, "arch.docx", buf.getvalue())
    assert "Architecture Overview" in res.text
    assert "workshop data plane" in res.text
    assert "Header 1 | Header 2" in res.text
    assert "Cell A | Cell B" in res.text


def test_parse_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Metric", "Value"])
    ws.append(["Accuracy", 0.94])
    ws.append(["Latency", "25ms"])

    buf = io.BytesIO()
    wb.save(buf)

    res = parse_document(DocumentFileType.XLSX, "metrics.xlsx", buf.getvalue())
    assert "=== Sheet: Summary ===" in res.text
    assert "Accuracy | 0.94" in res.text
    assert "Latency | 25ms" in res.text


def test_parse_image_metadata():
    img = PilImg.new("RGB", (120, 80), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    res = parse_document(DocumentFileType.IMAGE, "diagram.png", buf.getvalue())
    assert "120 x 80 pixels" in res.text
    assert "PNG" in res.text
    assert res.metadata.get("width") == 120
    assert res.metadata.get("height") == 80


def test_parse_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)

    res = parse_document(DocumentFileType.PDF, "blank.pdf", buf.getvalue())
    assert res.page_count == 1
