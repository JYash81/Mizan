"""File validation, magic-byte inspection, and decompression-bomb protection."""

import hashlib
import io
import re
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import PurePath

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_UNCOMPRESSED_ARCHIVE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_DECOMPRESSION_RATIO = 100.0  # 100:1
MAX_ARCHIVE_FILE_COUNT = 1000


class FileValidationError(Exception):
    """Base exception for file validation failures."""


class FileSizeLimitExceededError(FileValidationError):
    """Raised when file size exceeds maximum permitted threshold."""


class FileFormatUnsupportedError(FileValidationError):
    """Raised when file extension or magic bytes do not match supported types."""


class DecompressionBombDetectedError(FileValidationError):
    """Raised when archive compression ratio or uncompressed size exceeds safe bounds."""


class MalwareDetectedError(FileValidationError):
    """Raised when malware signature is detected."""


@dataclass(frozen=True)
class ValidatedFile:
    filename: str
    file_type: str  # PDF, DOCX, XLSX, CSV, TXT, JSON, JSONL, IMAGE
    mime_type: str
    size_bytes: int
    sha256: str
    content: bytes


class MalwareScanner(ABC):
    @abstractmethod
    def scan(self, filename: str, content: bytes) -> bool:
        """Returns True if clean, raises MalwareDetectedError if infected."""


class NullMalwareScanner(MalwareScanner):
    """Development scanner that passes all clean files."""

    def scan(self, filename: str, content: bytes) -> bool:
        return True


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename against path traversal, control chars, and illegal characters."""
    # Get basename only
    base = PurePath(filename).name
    # Strip dangerous characters
    cleaned = re.sub(r"[^\w\.\-\s]", "_", base).strip()
    # Remove leading dots or slashes
    cleaned = cleaned.lstrip(". ")
    if not cleaned:
        cleaned = "unnamed_document.bin"
    return cleaned[:255]


def _check_zip_bomb(content: bytes) -> None:
    """Verifies that a ZIP container does not exceed uncompressed size or ratio limits."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            infos = z.infolist()
            if len(infos) > MAX_ARCHIVE_FILE_COUNT:
                raise DecompressionBombDetectedError(
                    f"Archive file count ({len(infos)}) exceeds safety limit of {MAX_ARCHIVE_FILE_COUNT}."
                )

            total_uncompressed = 0
            total_compressed = len(content)

            for info in infos:
                # Reject nested archives
                lower_name = info.filename.lower()
                if lower_name.endswith((".zip", ".tar", ".gz", ".7z", ".rar", ".bz2")):
                    raise DecompressionBombDetectedError(
                        f"Nested archive forbidden inside office document: {info.filename}"
                    )
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_UNCOMPRESSED_ARCHIVE_BYTES:
                    raise DecompressionBombDetectedError(
                        f"Archive uncompressed size exceeds {MAX_UNCOMPRESSED_ARCHIVE_BYTES} bytes."
                    )

            if total_compressed > 0:
                ratio = total_uncompressed / total_compressed
                if ratio > MAX_DECOMPRESSION_RATIO:
                    raise DecompressionBombDetectedError(
                        f"Decompression ratio ({ratio:.1f}:1) exceeds limit of {MAX_DECOMPRESSION_RATIO}:1."
                    )
    except zipfile.BadZipFile as e:
        raise FileFormatUnsupportedError(f"Corrupt or invalid zip archive: {e}") from e


def validate_file_upload(
    filename: str,
    content: bytes,
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
    malware_scanner: MalwareScanner | None = None,
) -> ValidatedFile:
    """Validates file size, extension, magic bytes, decompression safety, and malware."""
    size_bytes = len(content)
    if size_bytes == 0:
        raise FileValidationError("File is empty (0 bytes).")

    if size_bytes > max_size_bytes:
        raise FileSizeLimitExceededError(
            f"File size ({size_bytes} bytes) exceeds maximum limit of {max_size_bytes} bytes."
        )

    safe_name = sanitize_filename(filename)
    ext = safe_name.lower().split(".")[-1] if "." in safe_name else ""

    # Magic byte inspection
    header_16 = content[:16]

    file_type: str
    mime_type: str

    if ext == "pdf":
        if not header_16.startswith(b"%PDF-"):
            raise FileFormatUnsupportedError("File has .pdf extension but lacks %PDF magic header.")
        file_type = "PDF"
        mime_type = "application/pdf"

    elif ext in ("docx", "doc"):
        if not header_16.startswith(b"PK\x03\x04"):
            raise FileFormatUnsupportedError(
                "File has .docx extension but lacks valid PK ZIP header."
            )
        _check_zip_bomb(content)
        file_type = "DOCX"
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    elif ext in ("xlsx", "xls"):
        if not header_16.startswith(b"PK\x03\x04"):
            raise FileFormatUnsupportedError(
                "File has .xlsx extension but lacks valid PK ZIP header."
            )
        _check_zip_bomb(content)
        file_type = "XLSX"
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    elif ext in ("csv", "tsv"):
        if b"\x00" in header_16:
            raise FileFormatUnsupportedError("CSV file contains null binary bytes.")
        file_type = "CSV"
        mime_type = "text/csv"

    elif ext in ("txt", "md", "text", "log"):
        if b"\x00" in header_16:
            raise FileFormatUnsupportedError("Text file contains null binary bytes.")
        file_type = "TXT"
        mime_type = "text/plain"

    elif ext == "json":
        if b"\x00" in header_16:
            raise FileFormatUnsupportedError("JSON file contains null binary bytes.")
        file_type = "JSON"
        mime_type = "application/json"

    elif ext == "jsonl":
        if b"\x00" in header_16:
            raise FileFormatUnsupportedError("JSONL file contains null binary bytes.")
        file_type = "JSONL"
        mime_type = "application/x-ndjson"

    elif ext in ("png", "jpg", "jpeg", "webp"):
        if ext == "png":
            if not header_16.startswith(b"\x89PNG\r\n\x1a\n"):
                raise FileFormatUnsupportedError("Invalid PNG magic header.")
            mime_type = "image/png"
        elif ext in ("jpg", "jpeg"):
            if not header_16.startswith(b"\xff\xd8\xff"):
                raise FileFormatUnsupportedError("Invalid JPEG magic header.")
            mime_type = "image/jpeg"
        else:  # webp
            if not (content[:4] == b"RIFF" and content[8:12] == b"WEBP"):
                raise FileFormatUnsupportedError("Invalid WebP magic header.")
            mime_type = "image/webp"
        file_type = "IMAGE"

    else:
        raise FileFormatUnsupportedError(
            f"Unsupported file format '{ext}'. Allowed: pdf, docx, xlsx, csv, txt, md, json, jsonl, png, jpg, webp."
        )

    # Malware check
    scanner = malware_scanner or NullMalwareScanner()
    scanner.scan(safe_name, content)

    sha256 = hashlib.sha256(content).hexdigest()

    return ValidatedFile(
        filename=safe_name,
        file_type=file_type,
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256=sha256,
        content=content,
    )
