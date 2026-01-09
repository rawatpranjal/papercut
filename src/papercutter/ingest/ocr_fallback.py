"""OCR fallback using pdfplumber for when Docling fails.

This module provides a fallback extraction path when Docling cannot
process a PDF (corrupted, scanned, or incompatible format).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from papercutter.exceptions import ExtractionError, InvalidPDFError
from papercutter.extractors.pdfplumber import PdfPlumberExtractor

logger = logging.getLogger(__name__)


@dataclass
class OCRTable:
    """A table extracted via OCR fallback."""

    page: int  # 0-indexed
    data: list[list[str]]  # 2D grid of cell values
    markdown: str | None = None


@dataclass
class OCRResult:
    """Result of OCR fallback extraction."""

    text: str
    """Full document text."""

    markdown: str
    """Basic Markdown formatting of text."""

    tables: list[OCRTable] = field(default_factory=list)
    """Extracted tables."""

    page_count: int = 0
    """Number of pages in the document."""

    title: str | None = None
    """Guessed title (first non-empty line)."""

    extraction_warnings: list[str] = field(default_factory=list)
    """Warnings during extraction."""


class OCRFallback:
    """OCR fallback using pdfplumber for basic text extraction.

    This is used when Docling fails to process a PDF. It provides
    basic text and table extraction without the advanced structure
    recognition that Docling provides.
    """

    def __init__(self, max_workers: int | None = None):
        """Initialize the OCR fallback.

        Args:
            max_workers: Max workers for parallel page extraction.
        """
        self._extractor = PdfPlumberExtractor(max_workers=max_workers)

    def extract(self, pdf_path: Path) -> OCRResult:
        """Extract text and tables from PDF using pdfplumber.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            OCRResult with text, markdown, and tables.

        Raises:
            ExtractionError: If extraction fails.
            InvalidPDFError: If PDF cannot be opened.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise ExtractionError(
                f"PDF file not found: {pdf_path.name}",
                details=f"Path: {pdf_path}",
            )

        warnings_list: list[str] = []

        try:
            # Get page count
            page_count = self._extractor.get_page_count(pdf_path)

            # Extract text per page for better structure
            page_texts = self._extractor.extract_text_by_page(pdf_path)
            full_text = "\n\n".join(text for _, text in page_texts if text)

            # Extract tables
            raw_tables = self._extractor.extract_tables(pdf_path)
            tables = self._process_tables(raw_tables)

            # Convert to basic markdown
            markdown = self._text_to_markdown(page_texts, tables)

            # Try to extract title from first page
            title = self._guess_title(page_texts)

            return OCRResult(
                text=full_text,
                markdown=markdown,
                tables=tables,
                page_count=page_count,
                title=title,
                extraction_warnings=warnings_list,
            )

        except InvalidPDFError:
            raise
        except Exception as e:
            raise ExtractionError(
                f"OCR fallback failed for {pdf_path.name}",
                details=str(e),
            ) from e

    def _process_tables(self, raw_tables: list[dict[str, Any]]) -> list[OCRTable]:
        """Convert pdfplumber tables to OCRTable format."""
        tables = []
        for table in raw_tables:
            page = table.get("page", 0)
            data = table.get("data", [])

            # Clean up table data
            cleaned_data = []
            for row in data:
                cleaned_row = [str(cell) if cell is not None else "" for cell in row]
                cleaned_data.append(cleaned_row)

            # Generate markdown for table
            md = self._table_to_markdown(cleaned_data)

            tables.append(
                OCRTable(
                    page=page,
                    data=cleaned_data,
                    markdown=md,
                )
            )

        return tables

    def _table_to_markdown(self, data: list[list[str]]) -> str:
        """Convert table data to Markdown table format."""
        if not data:
            return ""

        lines = []

        # Header row
        if len(data) > 0:
            header = data[0]
            lines.append("| " + " | ".join(str(c) for c in header) + " |")
            lines.append("|" + "|".join("---" for _ in header) + "|")

        # Data rows
        for row in data[1:]:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")

        return "\n".join(lines)

    def _text_to_markdown(
        self,
        page_texts: list[tuple[int, str]],
        tables: list[OCRTable],
    ) -> str:
        """Convert extracted text to basic Markdown.

        Attempts to detect:
        - Headers (lines in all caps or short lines followed by longer text)
        - Paragraphs (blocks of text separated by blank lines)
        - Lists (lines starting with bullets or numbers)
        """
        # Create a map of page -> tables
        tables_by_page: dict[int, list[OCRTable]] = {}
        for table in tables:
            if table.page not in tables_by_page:
                tables_by_page[table.page] = []
            tables_by_page[table.page].append(table)

        markdown_parts = []

        for page_num, text in page_texts:
            if not text.strip():
                continue

            # Process text into markdown
            page_md = self._process_page_text(text)
            markdown_parts.append(page_md)

            # Add tables for this page
            if page_num in tables_by_page:
                for table in tables_by_page[page_num]:
                    if table.markdown:
                        markdown_parts.append(f"\n{table.markdown}\n")

            # Add page separator
            markdown_parts.append(f"\n---\n*Page {page_num + 1}*\n")

        return "\n".join(markdown_parts)

    def _process_page_text(self, text: str) -> str:
        """Process a single page's text into Markdown."""
        lines = text.split("\n")
        processed = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                processed.append("")
                i += 1
                continue

            # Check for potential header
            if self._is_potential_header(line, lines, i):
                # Determine header level based on characteristics
                level = self._determine_header_level(line)
                processed.append(f"\n{'#' * level} {line}\n")
                i += 1
                continue

            # Check for list item
            if self._is_list_item(line):
                processed.append(self._format_list_item(line))
                i += 1
                continue

            # Regular paragraph text
            processed.append(line)
            i += 1

        return "\n".join(processed)

    def _is_potential_header(
        self, line: str, lines: list[str], index: int
    ) -> bool:
        """Check if a line looks like a header."""
        # All caps short line
        if line.isupper() and len(line) < 80:
            return True

        # Numbered section (1. Introduction, 2.1 Methods)
        if re.match(r"^\d+\.?\d*\s+[A-Z]", line):
            return True

        # Short line followed by longer paragraph
        if len(line) < 60 and index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if len(next_line) > 100:
                return True

        return False

    def _determine_header_level(self, line: str) -> int:
        """Determine Markdown header level for a line."""
        # Check for section numbers
        match = re.match(r"^(\d+)(\.(\d+))?(\.(\d+))?\s", line)
        if match:
            if match.group(5):  # X.Y.Z format
                return 4
            if match.group(3):  # X.Y format
                return 3
            return 2  # X format

        # All caps = major header
        if line.isupper():
            return 2

        return 3  # Default to h3

    def _is_list_item(self, line: str) -> bool:
        """Check if a line is a list item."""
        # Bullet points
        if re.match(r"^[•\-\*]\s", line):
            return True

        # Numbered list
        if re.match(r"^\d+[\.\)]\s", line):
            return True

        # Lettered list
        if re.match(r"^[a-z][\.\)]\s", line, re.IGNORECASE):
            return True

        return False

    def _format_list_item(self, line: str) -> str:
        """Format a line as a Markdown list item."""
        # Normalize bullet points
        if re.match(r"^[•\*]\s", line):
            return "- " + line[2:]

        # Numbered list - keep as is but ensure proper format
        match = re.match(r"^(\d+)[\.\)]\s(.+)", line)
        if match:
            return f"{match.group(1)}. {match.group(2)}"

        # Lettered list - convert to numbered
        match = re.match(r"^[a-z][\.\)]\s(.+)", line, re.IGNORECASE)
        if match:
            return f"- {match.group(1)}"

        return line

    def _guess_title(self, page_texts: list[tuple[int, str]]) -> str | None:
        """Attempt to guess the document title from first page."""
        if not page_texts:
            return None

        _, first_page = page_texts[0]
        lines = first_page.strip().split("\n")

        # Look for first substantial line
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 10 and len(line) < 200:
                # Skip lines that look like headers/footers
                if re.match(r"^\d+$", line):  # Just a number
                    continue
                if re.match(r"^page\s+\d+", line, re.IGNORECASE):
                    continue
                return line

        return None


def extract_with_fallback(pdf_path: Path) -> OCRResult:
    """Convenience function for OCR fallback extraction.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        OCRResult with extracted content.
    """
    fallback = OCRFallback()
    return fallback.extract(pdf_path)
