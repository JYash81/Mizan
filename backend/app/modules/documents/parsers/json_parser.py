"""Structured JSON and JSONL document parser."""

import json

from app.modules.documents.parsers.base import (
    BaseParser,
    ExtractedDocumentResult,
    ParserError,
    compute_metrics,
)


class JsonParser(BaseParser):
    def parse(self, filename: str, content: bytes) -> ExtractedDocumentResult:
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ParserError(f"JSON file '{filename}' must be valid UTF-8: {e}") from e

        if filename.lower().endswith(".jsonl"):
            lines = decoded.strip().splitlines()
            records: list[str] = []
            for i, line in enumerate(lines, 1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    obj = json.loads(clean_line)
                    records.append(f"Record {i}: {json.dumps(obj, indent=2)}")
                except json.JSONDecodeError as err:
                    raise ParserError(f"Invalid JSON at line {i} in '{filename}': {err}") from err
            formatted_text = "\n\n".join(records)
            return compute_metrics(formatted_text, metadata={"record_count": len(records)})

        # Standard .json
        try:
            parsed = json.loads(decoded)
            formatted_text = json.dumps(parsed, indent=2)
            return compute_metrics(formatted_text, metadata={"is_array": isinstance(parsed, list)})
        except json.JSONDecodeError as err:
            raise ParserError(f"Invalid JSON file '{filename}': {err}") from err
