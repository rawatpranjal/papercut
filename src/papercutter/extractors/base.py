"""Base protocol for PDF extraction backends."""

from pathlib import Path
from typing import Any, Optional, Protocol


class Extractor(Protocol):
    """Protocol defining the interface for PDF extraction backends."""

    def extract_text(self, path: Path, pages: Optional[list[int]] = None) -> str:
        """Extract text from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers to extract.
                   If None, extract all pages.

        Returns:
            Extracted text as a string.
        """
        ...

    def extract_tables(
        self, path: Path, pages: Optional[list[int]] = None
    ) -> list[dict[str, Any]]:
        """Extract tables from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers to extract.
                   If None, extract from all pages.

        Returns:
            List of dictionaries containing table data and metadata.
        """
        ...

    def get_page_count(self, path: Path) -> int:
        """Get the number of pages in the PDF.

        Args:
            path: Path to the PDF file.

        Returns:
            Number of pages.
        """
        ...

    def extract_text_by_page(
        self, path: Path, pages: Optional[list[int]] = None
    ) -> list[tuple[int, str]]:
        """Extract text from PDF, returning per-page results.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.
                   If None, extract all pages.

        Returns:
            List of (page_number, text) tuples where page_number is 0-indexed.
        """
        ...
