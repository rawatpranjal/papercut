"""Table extraction logic."""

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from papercut.extractors.base import Extractor


@dataclass
class ExtractedTable:
    """Represents an extracted table from a PDF."""

    page: int
    data: list[list[str]]
    bbox: Optional[tuple[float, float, float, float]] = None

    @property
    def rows(self) -> int:
        """Number of rows in the table."""
        return len(self.data)

    @property
    def cols(self) -> int:
        """Number of columns in the table."""
        return len(self.data[0]) if self.data else 0

    @property
    def headers(self) -> list[str]:
        """Get the first row as headers."""
        return self.data[0] if self.data else []

    def to_csv(self) -> str:
        """Convert table to CSV string.

        Returns:
            CSV formatted string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        for row in self.data:
            # Clean up cell values
            cleaned_row = [self._clean_cell(cell) for cell in row]
            writer.writerow(cleaned_row)

        return output.getvalue()

    def to_json(self) -> str:
        """Convert table to JSON string.

        Returns:
            JSON formatted string with table data.
        """
        # Clean up data
        cleaned_data = [
            [self._clean_cell(cell) for cell in row] for row in self.data
        ]

        return json.dumps(
            {
                "page": self.page,
                "rows": self.rows,
                "cols": self.cols,
                "data": cleaned_data,
            },
            indent=2,
        )

    def to_dict_rows(self) -> list[dict[str, str]]:
        """Convert table to list of dictionaries using first row as headers.

        Returns:
            List of row dictionaries.
        """
        if len(self.data) < 2:
            return []

        headers = [self._clean_cell(h) or f"col_{i}" for i, h in enumerate(self.headers)]
        rows = []

        for row in self.data[1:]:
            row_dict = {}
            for i, cell in enumerate(row):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_dict[key] = self._clean_cell(cell)
            rows.append(row_dict)

        return rows

    def _clean_cell(self, cell: Any) -> str:
        """Clean a cell value.

        Args:
            cell: Raw cell value.

        Returns:
            Cleaned string value.
        """
        if cell is None:
            return ""
        # Convert to string and clean whitespace
        return str(cell).strip().replace("\n", " ")


class TableExtractor:
    """Extract tables from PDFs."""

    def __init__(self, backend: Extractor):
        """Initialize with an extraction backend.

        Args:
            backend: PDF extraction backend (e.g., PdfPlumberExtractor).
        """
        self.backend = backend

    def extract(
        self, path: Path, pages: Optional[list[int]] = None
    ) -> list[ExtractedTable]:
        """Extract all tables from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.

        Returns:
            List of ExtractedTable objects.
        """
        raw_tables = self.backend.extract_tables(path, pages)

        return [
            ExtractedTable(
                page=table["page"],
                data=table["data"],
                bbox=table.get("bbox"),
            )
            for table in raw_tables
            if table["data"]  # Skip empty tables
        ]

    def extract_as_csv(
        self, path: Path, pages: Optional[list[int]] = None
    ) -> list[tuple[int, str]]:
        """Extract all tables as CSV strings.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.

        Returns:
            List of (page_number, csv_string) tuples.
        """
        tables = self.extract(path, pages)
        return [(t.page, t.to_csv()) for t in tables]
