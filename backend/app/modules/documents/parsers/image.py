"""Image metadata parser using Pillow."""

import io

from PIL import Image as PilImage

from app.modules.documents.parsers.base import (
    BaseParser,
    ExtractedDocumentResult,
    ParserError,
    compute_metrics,
)


class ImageParser(BaseParser):
    def parse(self, filename: str, content: bytes) -> ExtractedDocumentResult:
        try:
            with PilImage.open(io.BytesIO(content)) as img:
                img_format = img.format or "UNKNOWN"
                width, height = img.size
                mode = img.mode
        except Exception as e:
            raise ParserError(f"Failed to inspect image '{filename}': {e}") from e

        text = (
            f"[Image Attachment: {filename}]\n"
            f"Format: {img_format}\n"
            f"Dimensions: {width} x {height} pixels\n"
            f"Color Mode: {mode}\n"
            f"Note: Text extraction for images requires downstream OCR or Vision provider."
        )

        return compute_metrics(
            text,
            metadata={"format": img_format, "width": width, "height": height, "mode": mode},
        )
