"""PDF extraction backend using pdfplumber."""

from pathlib import Path
from typing import Any, Optional

import pdfplumber

from papercut.exceptions import ExtractionError, InvalidPDFError


class PdfPlumberExtractor:
    """PDF extraction backend using pdfplumber library."""

    def extract_text(self, path: Path, pages: Optional[list[int]] = None) -> str:
        """Extract text from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers to extract.
                   If None, extract all pages.

        Returns:
            Extracted text as a string.

        Raises:
            InvalidPDFError: If the PDF cannot be opened.
            ExtractionError: If text extraction fails.
        """
        try:
            with pdfplumber.open(path) as pdf:
                if pages is None:
                    target_pages = pdf.pages
                else:
                    # Filter to valid page indices
                    valid_pages = [i for i in pages if 0 <= i < len(pdf.pages)]
                    target_pages = [pdf.pages[i] for i in valid_pages]

                text_parts = []
                for page in target_pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                return "\n\n".join(text_parts)

        except Exception as e:
            if "Invalid" in str(e) or "corrupt" in str(e).lower():
                raise InvalidPDFError(
                    f"Cannot open PDF: {path.name}",
                    details=str(e),
                ) from e
            raise ExtractionError(
                f"Failed to extract text from {path.name}",
                details=str(e),
            ) from e

    def extract_tables(
        self, path: Path, pages: Optional[list[int]] = None
    ) -> list[dict[str, Any]]:
        """Extract tables from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers to extract.
                   If None, extract from all pages.

        Returns:
            List of dictionaries containing:
                - page: 0-indexed page number
                - data: 2D list of cell values
                - bbox: Bounding box tuple (x0, y0, x1, y1)

        Raises:
            InvalidPDFError: If the PDF cannot be opened.
            ExtractionError: If table extraction fails.
        """
        try:
            tables = []
            with pdfplumber.open(path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    if pages is not None and page_idx not in pages:
                        continue

                    page_tables = page.extract_tables()
                    for table_data in page_tables:
                        if table_data:  # Skip empty tables
                            tables.append(
                                {
                                    "page": page_idx,
                                    "data": table_data,
                                    "bbox": None,  # Could extract from table settings
                                }
                            )

            return tables

        except Exception as e:
            if "Invalid" in str(e) or "corrupt" in str(e).lower():
                raise InvalidPDFError(
                    f"Cannot open PDF: {path.name}",
                    details=str(e),
                ) from e
            raise ExtractionError(
                f"Failed to extract tables from {path.name}",
                details=str(e),
            ) from e

    def get_page_count(self, path: Path) -> int:
        """Get the number of pages in the PDF.

        Args:
            path: Path to the PDF file.

        Returns:
            Number of pages.

        Raises:
            InvalidPDFError: If the PDF cannot be opened.
        """
        try:
            with pdfplumber.open(path) as pdf:
                return len(pdf.pages)
        except Exception as e:
            raise InvalidPDFError(
                f"Cannot open PDF: {path.name}",
                details=str(e),
            ) from e
