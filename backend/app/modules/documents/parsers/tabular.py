"""Tabular document parsers for CSV and XLSX."""

import csv
import io

import openpyxl

from app.modules.documents.parsers.base import (
    BaseParser,
    ExtractedDocumentResult,
    ParserError,
    compute_metrics,
)

MAX_CSV_ROWS = 50_000
MAX_XLSX_CELLS = 50_000


class CsvParser(BaseParser):
    def parse(self, filename: str, content: bytes) -> ExtractedDocumentResult:
        try:
            try:
                decoded = content.decode("utf-8")
            except UnicodeDecodeError:
                decoded = content.decode("latin-1")
        except Exception as e:
            raise ParserError(f"Failed to decode CSV '{filename}': {e}") from e

        delimiter = "\t" if filename.lower().endswith(".tsv") else ","
        reader = csv.reader(io.StringIO(decoded), delimiter=delimiter)

        lines: list[str] = []
        row_count = 0

        for row in reader:
            row_count += 1
            if row_count > MAX_CSV_ROWS:
                lines.append(f"\n[Note: Truncated after {MAX_CSV_ROWS} rows for performance]")
                break
            lines.append(" | ".join(row))

        formatted_text = "\n".join(lines)
        return compute_metrics(formatted_text, metadata={"row_count": row_count})


class XlsxParser(BaseParser):
    def parse(self, filename: str, content: bytes) -> ExtractedDocumentResult:
        try:
            workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as e:
            raise ParserError(f"Failed to open Excel workbook '{filename}': {e}") from e

        sheet_texts: list[str] = []
        total_cells = 0
        limit_reached = False

        try:
            for sheetname in workbook.sheetnames:
                sheet = workbook[sheetname]
                sheet_lines = [f"=== Sheet: {sheetname} ==="]

                for row in sheet.iter_rows(values_only=True):
                    row_vals = [str(v) if v is not None else "" for v in row]
                    total_cells += len(row_vals)
                    sheet_lines.append(" | ".join(row_vals))

                    if total_cells >= MAX_XLSX_CELLS:
                        sheet_lines.append(f"\n[Note: Truncated after {MAX_XLSX_CELLS} cells]")
                        limit_reached = True
                        break

                sheet_texts.append("\n".join(sheet_lines))
                if limit_reached:
                    break
        finally:
            workbook.close()

        full_text = "\n\n".join(sheet_texts)
        return compute_metrics(
            full_text, metadata={"sheets": workbook.sheetnames, "total_cells": total_cells}
        )
