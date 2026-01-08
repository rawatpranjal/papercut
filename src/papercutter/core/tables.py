"""Table extraction logic."""

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from papercutter.extractors.base import Extractor


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

    # Pre-compiled pattern for figure reference detection
    _FIGURE_PATTERN = re.compile(r"(?i)^fig(?:ure)?\.?\s*\d|^image\s*\d")

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

        validated_tables = []
        for table in raw_tables:
            if not table["data"]:  # Skip empty tables
                continue

            # Validate that this looks like a real table
            if self._is_valid_table(table["data"]):
                validated_tables.append(
                    ExtractedTable(
                        page=table["page"],
                        data=table["data"],
                        bbox=table.get("bbox"),
                    )
                )

        return validated_tables

    def _is_valid_table(self, data: list[list[Any]]) -> bool:
        """Validate that data looks like a real table, not a figure or noise.

        Filters out:
        - Single column "tables" (likely figure text)
        - Inconsistent column counts (likely OCR noise)
        - Mostly empty cells (sparse/broken extraction)
        - Figure references (text like "Figure 1", "Fig. 2")

        Uses single-pass iteration for efficiency.

        Args:
            data: 2D list of cell values.

        Returns:
            True if this looks like a valid table.
        """
        if not data or len(data) < 2:
            return False

        # Single pass to collect all statistics
        col_count_freq: dict[int, int] = {}
        total_cells = 0
        non_empty_cells = 0
        figure_refs = 0
        garbled_count = 0

        for row in data:
            row_len = len(row)
            col_count_freq[row_len] = col_count_freq.get(row_len, 0) + 1
            total_cells += row_len

            for cell in row:
                if cell:
                    cell_str = str(cell).strip()
                    if cell_str:
                        non_empty_cells += 1

                        # Check for figure reference
                        if self._FIGURE_PATTERN.match(cell_str):
                            figure_refs += 1

                        # Check for garbled text (reversed OCR)
                        if len(cell_str) > 5:
                            words = cell_str.split()
                            if words:
                                # All words with len > 2 start and end with uppercase
                                long_words = [w for w in words if len(w) > 2]
                                if long_words and all(
                                    w[0].isupper() and w[-1].isupper()
                                    for w in long_words
                                ):
                                    garbled_count += 1

        if not col_count_freq:
            return False

        # Find most common column count
        most_common_cols = max(col_count_freq.keys(), key=lambda k: col_count_freq[k])

        # Require at least 2 columns
        if most_common_cols < 2:
            return False

        # Require most rows to have consistent column count (70% threshold)
        consistent_rows = col_count_freq[most_common_cols]
        if consistent_rows < len(data) * 0.7:
            return False

        # Require at least 30% non-empty cells
        if total_cells == 0 or non_empty_cells / total_cells < 0.3:
            return False

        # Reject if too many cells look like figure references
        if figure_refs / total_cells > 0.2:
            return False

        # Reject if it looks like reversed/garbled text (common OCR issue)
        if garbled_count / total_cells > 0.3:
            return False

        return True

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
