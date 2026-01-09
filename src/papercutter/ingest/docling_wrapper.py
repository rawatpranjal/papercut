"""Docling wrapper for PDF to Markdown conversion.

Docling is a PDF conversion library that produces high-quality Markdown
with proper table handling. This wrapper provides lazy loading and
graceful error handling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from papercutter.exceptions import ExtractionError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """A table extracted from a PDF."""

    page: int  # 0-indexed
    data: list[list[str]]  # 2D grid of cell values
    caption: str | None = None
    markdown: str | None = None  # Markdown representation


@dataclass
class DoclingResult:
    """Result of Docling PDF conversion."""

    markdown: str
    """Full document as Markdown."""

    tables: list[ExtractedTable] = field(default_factory=list)
    """Extracted tables with structure."""

    title: str | None = None
    """Detected document title."""

    authors: list[str] = field(default_factory=list)
    """Detected authors."""

    abstract: str | None = None
    """Detected abstract text."""

    page_count: int = 0
    """Number of pages in the document."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata from Docling."""


class DoclingWrapper:
    """Wrapper around Docling for PDF → Markdown conversion.

    Docling is lazy-loaded to avoid import overhead when not used.
    Falls back gracefully if Docling is not installed.
    """

    _docling_available: bool | None = None

    @classmethod
    def is_available(cls) -> bool:
        """Check if Docling is installed and available."""
        if cls._docling_available is None:
            try:
                import docling  # noqa: F401

                cls._docling_available = True
            except ImportError:
                cls._docling_available = False
        return cls._docling_available

    def __init__(self, ocr_enabled: bool = True):
        """Initialize the Docling wrapper.

        Args:
            ocr_enabled: Whether to use OCR for scanned pages.
        """
        self.ocr_enabled = ocr_enabled
        self._converter = None

    def _get_converter(self) -> Any:
        """Get or create the Docling converter (lazy initialization)."""
        if self._converter is not None:
            return self._converter

        if not self.is_available():
            raise ExtractionError(
                "Docling is not installed",
                details="Install with: pip install papercutter[docling]",
            )

        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = self.ocr_enabled
            pipeline_options.do_table_structure = True

            self._converter = DocumentConverter(
                allowed_formats=[InputFormat.PDF],
                format_options={
                    InputFormat.PDF: pipeline_options,
                },
            )
            return self._converter

        except Exception as e:
            raise ExtractionError(
                "Failed to initialize Docling",
                details=str(e),
            ) from e

    def convert(self, pdf_path: Path) -> DoclingResult:
        """Convert a PDF to Markdown using Docling.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            DoclingResult with markdown and extracted metadata.

        Raises:
            ExtractionError: If conversion fails.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise ExtractionError(
                f"PDF file not found: {pdf_path.name}",
                details=f"Path: {pdf_path}",
            )

        try:
            converter = self._get_converter()
            result = converter.convert(str(pdf_path))

            # Extract document from result
            doc = result.document

            # Get markdown export
            markdown = doc.export_to_markdown()

            # Extract tables
            tables = self._extract_tables(doc)

            # Extract metadata
            title = self._extract_title(doc)
            authors = self._extract_authors(doc)
            abstract = self._extract_abstract(doc)

            return DoclingResult(
                markdown=markdown,
                tables=tables,
                title=title,
                authors=authors,
                abstract=abstract,
                page_count=doc.num_pages if hasattr(doc, "num_pages") else 0,
                metadata=self._extract_metadata(doc),
            )

        except ExtractionError:
            raise
        except Exception as e:
            error_msg = str(e).lower()

            # Check for common failure modes
            if "corrupt" in error_msg or "invalid" in error_msg:
                raise ExtractionError(
                    f"PDF appears corrupt: {pdf_path.name}",
                    details=str(e),
                    hint="Try the OCR fallback with: --fallback",
                ) from e

            if "memory" in error_msg or "oom" in error_msg:
                raise ExtractionError(
                    f"PDF too large for Docling: {pdf_path.name}",
                    details="Consider splitting the PDF first.",
                    hint="Use the splitter for large books.",
                ) from e

            raise ExtractionError(
                f"Docling conversion failed for {pdf_path.name}",
                details=str(e),
            ) from e

    def _extract_tables(self, doc: Any) -> list[ExtractedTable]:
        """Extract tables from Docling document."""
        tables = []

        try:
            # Docling provides tables in the document structure
            if hasattr(doc, "tables"):
                for i, table in enumerate(doc.tables):
                    page = getattr(table, "page", 0)
                    caption = getattr(table, "caption", None)

                    # Get table data as 2D array
                    data = []
                    if hasattr(table, "data"):
                        data = table.data
                    elif hasattr(table, "to_dataframe"):
                        df = table.to_dataframe()
                        data = [df.columns.tolist()] + df.values.tolist()

                    # Get markdown representation
                    md = None
                    if hasattr(table, "export_to_markdown"):
                        md = table.export_to_markdown()

                    tables.append(
                        ExtractedTable(
                            page=page,
                            data=data,
                            caption=caption,
                            markdown=md,
                        )
                    )
        except Exception as e:
            logger.debug(f"Failed to extract tables: {e}")

        return tables

    def _extract_title(self, doc: Any) -> str | None:
        """Extract document title from Docling document."""
        try:
            if hasattr(doc, "title") and doc.title:
                return str(doc.title)
            if hasattr(doc, "metadata") and doc.metadata:
                return doc.metadata.get("title")
        except Exception:
            pass
        return None

    def _extract_authors(self, doc: Any) -> list[str]:
        """Extract authors from Docling document."""
        try:
            if hasattr(doc, "authors"):
                return list(doc.authors)
            if hasattr(doc, "metadata") and doc.metadata:
                authors = doc.metadata.get("authors", [])
                if isinstance(authors, str):
                    return [authors]
                return list(authors)
        except Exception:
            pass
        return []

    def _extract_abstract(self, doc: Any) -> str | None:
        """Extract abstract from Docling document."""
        try:
            if hasattr(doc, "abstract") and doc.abstract:
                return str(doc.abstract)
            if hasattr(doc, "metadata") and doc.metadata:
                return doc.metadata.get("abstract")
        except Exception:
            pass
        return None

    def _extract_metadata(self, doc: Any) -> dict[str, Any]:
        """Extract additional metadata from Docling document."""
        metadata: dict[str, Any] = {}
        try:
            if hasattr(doc, "metadata") and doc.metadata:
                if isinstance(doc.metadata, dict):
                    metadata.update(doc.metadata)
                else:
                    # Try to convert to dict
                    metadata = dict(doc.metadata)
        except Exception:
            pass
        return metadata


def convert_pdf(pdf_path: Path, ocr_enabled: bool = True) -> DoclingResult:
    """Convenience function to convert a PDF to Markdown.

    Args:
        pdf_path: Path to the PDF file.
        ocr_enabled: Whether to use OCR for scanned pages.

    Returns:
        DoclingResult with markdown and metadata.
    """
    wrapper = DoclingWrapper(ocr_enabled=ocr_enabled)
    return wrapper.convert(pdf_path)
