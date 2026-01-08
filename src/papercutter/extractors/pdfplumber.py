"""PDF extraction backend using pdfplumber."""

import os
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pdfplumber

from papercutter.exceptions import ExtractionError, InvalidPDFError


def _validate_page_indices(
    pages: list[int], total_pages: int
) -> list[int]:
    """Validate and filter page indices, warning about invalid ones.

    Args:
        pages: List of requested 0-indexed page numbers.
        total_pages: Total number of pages in the document.

    Returns:
        List of valid page indices.
    """
    valid = []
    invalid = []
    for i in pages:
        if 0 <= i < total_pages:
            valid.append(i)
        else:
            invalid.append(i)

    if invalid:
        warnings.warn(
            f"Ignoring invalid page indices {invalid} "
            f"(document has {total_pages} pages, valid range: 0-{total_pages - 1})",
            UserWarning,
            stacklevel=3,
        )

    return valid

# Minimum pages to benefit from parallel processing
_MIN_PAGES_FOR_PARALLEL = 10


def _extract_page_text(args: tuple[str, int]) -> tuple[int, str]:
    """Extract text from a single page (for parallel processing).

    Args:
        args: Tuple of (pdf_path, page_index).

    Returns:
        Tuple of (page_index, extracted_text).
    """
    pdf_path, page_idx = args
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_idx]
            return (page_idx, page.extract_text(layout=True) or "")
    except Exception:
        return (page_idx, "")


def _extract_page_tables(args: tuple[str, int]) -> tuple[int, list[list[Any]]]:
    """Extract tables from a single page (for parallel processing).

    Args:
        args: Tuple of (pdf_path, page_index).

    Returns:
        Tuple of (page_index, list_of_tables).
    """
    pdf_path, page_idx = args
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_idx]
            tables = page.extract_tables()
            return (page_idx, [t for t in tables if t])
    except Exception:
        return (page_idx, [])


class PdfPlumberExtractor:
    """PDF extraction backend using pdfplumber library."""

    def __init__(self, max_workers: int | None = None):
        """Initialize the extractor.

        Args:
            max_workers: Maximum number of worker processes for parallel extraction.
                        Defaults to min(4, cpu_count) to avoid overwhelming the system.
        """
        self.max_workers = max_workers or min(4, os.cpu_count() or 1)

    def extract_text(
        self,
        path: Path,
        pages: list[int] | None = None,
        parallel: bool = False,
    ) -> str:
        """Extract text from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers to extract.
                   If None, extract all pages.
            parallel: Use parallel processing for large documents.
                     Automatically enabled for documents with 10+ pages.

        Returns:
            Extracted text as a string.

        Raises:
            InvalidPDFError: If the PDF cannot be opened.
            ExtractionError: If text extraction fails.
        """
        try:
            with pdfplumber.open(path) as pdf:
                total_pages = len(pdf.pages)
                if pages is None:
                    target_indices = list(range(total_pages))
                else:
                    target_indices = _validate_page_indices(pages, total_pages)

                # Use parallel extraction for large documents
                use_parallel = parallel or len(target_indices) >= _MIN_PAGES_FOR_PARALLEL

                if use_parallel and len(target_indices) >= _MIN_PAGES_FOR_PARALLEL:
                    try:
                        return self._extract_text_parallel(path, target_indices)
                    except (RuntimeError, OSError, FileNotFoundError, BrokenPipeError) as e:
                        # Fall back to sequential on macOS multiprocessing issues
                        # (e.g., spawn errors when running from stdin/Jupyter)
                        error_str = str(e).lower()
                        if any(kw in error_str for kw in ("spawn", "stdin", "fork", "pickle", "broken pipe")):
                            pass  # Fall through to sequential
                        else:
                            raise

                # Sequential extraction
                text_parts = []
                for idx in target_indices:
                    page_text = pdf.pages[idx].extract_text(layout=True)
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

    def _extract_text_parallel(self, path: Path, page_indices: list[int]) -> str:
        """Extract text from multiple pages in parallel.

        Args:
            path: Path to the PDF file.
            page_indices: List of 0-indexed page numbers.

        Returns:
            Combined extracted text.
        """
        path_str = str(path.absolute())
        args = [(path_str, idx) for idx in page_indices]

        results: dict[int, str] = {}
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_extract_page_text, arg): arg[1] for arg in args}
            for future in as_completed(futures):
                page_idx, text = future.result()
                results[page_idx] = text

        # Combine in order
        text_parts = [results[idx] for idx in sorted(results.keys()) if results[idx]]
        return "\n\n".join(text_parts)

    def extract_tables(
        self,
        path: Path,
        pages: list[int] | None = None,
        parallel: bool = False,
    ) -> list[dict[str, Any]]:
        """Extract tables from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers to extract.
                   If None, extract from all pages.
            parallel: Use parallel processing for large documents.
                     Automatically enabled for documents with 10+ pages.

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
            with pdfplumber.open(path) as pdf:
                total_pages = len(pdf.pages)
                if pages is None:
                    target_indices = list(range(total_pages))
                else:
                    target_indices = _validate_page_indices(pages, total_pages)

                # Use parallel extraction for large documents
                use_parallel = parallel or len(target_indices) >= _MIN_PAGES_FOR_PARALLEL

                if use_parallel and len(target_indices) >= _MIN_PAGES_FOR_PARALLEL:
                    try:
                        return self._extract_tables_parallel(path, target_indices)
                    except (RuntimeError, OSError, FileNotFoundError, BrokenPipeError) as e:
                        # Fall back to sequential on macOS multiprocessing issues
                        error_str = str(e).lower()
                        if any(kw in error_str for kw in ("spawn", "stdin", "fork", "pickle", "broken pipe")):
                            pass  # Fall through to sequential
                        else:
                            raise

                # Sequential extraction
                tables = []
                for page_idx in target_indices:
                    page_tables = pdf.pages[page_idx].extract_tables()
                    for table_data in page_tables:
                        if table_data:
                            tables.append({
                                "page": page_idx,
                                "data": table_data,
                                "bbox": None,
                            })

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

    def _extract_tables_parallel(
        self, path: Path, page_indices: list[int]
    ) -> list[dict[str, Any]]:
        """Extract tables from multiple pages in parallel.

        Args:
            path: Path to the PDF file.
            page_indices: List of 0-indexed page numbers.

        Returns:
            List of table dictionaries.
        """
        path_str = str(path.absolute())
        args = [(path_str, idx) for idx in page_indices]

        page_results: dict[int, list[list[Any]]] = {}
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_extract_page_tables, arg): arg[1] for arg in args}
            for future in as_completed(futures):
                page_idx, tables = future.result()
                page_results[page_idx] = tables

        # Combine in page order
        all_tables = []
        for page_idx in sorted(page_results.keys()):
            for table_data in page_results[page_idx]:
                all_tables.append({
                    "page": page_idx,
                    "data": table_data,
                    "bbox": None,
                })

        return all_tables

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

    def extract_text_by_page(
        self,
        path: Path,
        pages: list[int] | None = None,
        parallel: bool = False,
    ) -> list[tuple[int, str]]:
        """Extract text from PDF, returning per-page results.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.
                   If None, extract all pages.
            parallel: Use parallel processing for large documents.
                     Automatically enabled for documents with 10+ pages.

        Returns:
            List of (page_number, text) tuples where page_number is 0-indexed.

        Raises:
            InvalidPDFError: If the PDF cannot be opened.
            ExtractionError: If text extraction fails.
        """
        try:
            with pdfplumber.open(path) as pdf:
                total_pages = len(pdf.pages)
                if pages is None:
                    target_indices = list(range(total_pages))
                else:
                    target_indices = _validate_page_indices(pages, total_pages)

                # Use parallel extraction for large documents
                use_parallel = parallel or len(target_indices) >= _MIN_PAGES_FOR_PARALLEL

                if use_parallel and len(target_indices) >= _MIN_PAGES_FOR_PARALLEL:
                    try:
                        return self._extract_text_by_page_parallel(path, target_indices)
                    except (RuntimeError, OSError, FileNotFoundError, BrokenPipeError) as e:
                        # Fall back to sequential on macOS multiprocessing issues
                        error_str = str(e).lower()
                        if any(kw in error_str for kw in ("spawn", "stdin", "fork", "pickle", "broken pipe")):
                            pass  # Fall through to sequential
                        else:
                            raise

                # Sequential extraction
                results = []
                for page_idx in target_indices:
                    page = pdf.pages[page_idx]
                    page_text = page.extract_text(layout=True) or ""
                    results.append((page_idx, page_text))

                return results

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

    def _extract_text_by_page_parallel(
        self, path: Path, page_indices: list[int]
    ) -> list[tuple[int, str]]:
        """Extract text from multiple pages in parallel, returning per-page results.

        Args:
            path: Path to the PDF file.
            page_indices: List of 0-indexed page numbers.

        Returns:
            List of (page_number, text) tuples in page order.
        """
        path_str = str(path.absolute())
        args = [(path_str, idx) for idx in page_indices]

        results: dict[int, str] = {}
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_extract_page_text, arg): arg[1] for arg in args}
            for future in as_completed(futures):
                page_idx, text = future.result()
                results[page_idx] = text

        # Return in page order
        return [(idx, results[idx]) for idx in sorted(results.keys())]
