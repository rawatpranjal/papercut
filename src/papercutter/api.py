"""Convenience API for Papercutter.

This module provides simple, high-level functions for common tasks:

    >>> from papercutter import fetch_arxiv, extract_text
    >>> doc = fetch_arxiv("1706.03762", "/tmp")
    >>> text = extract_text(doc.path)

For more control, use the underlying classes directly.
"""

from pathlib import Path
from typing import Union, cast

from papercutter.extractors.pdfplumber import PdfPlumberExtractor
from papercutter.legacy.core.figures import ExtractedFigure, FigureExtractor
from papercutter.legacy.core.references import Reference, ReferenceExtractor
from papercutter.legacy.core.tables import ExtractedTable, TableExtractor
from papercutter.legacy.core.text import TextExtractor
from papercutter.legacy.fetchers.arxiv import ArxivFetcher
from papercutter.legacy.fetchers.base import Document
from papercutter.legacy.fetchers.doi import DOIFetcher
from papercutter.legacy.fetchers.nber import NBERFetcher
from papercutter.legacy.fetchers.registry import get_registry
from papercutter.legacy.fetchers.ssrn import SSRNFetcher
from papercutter.legacy.fetchers.url import URLFetcher

PathLike = Union[Path, str]


# =============================================================================
# Fetcher convenience functions
# =============================================================================


def fetch_arxiv(arxiv_id: str, output_dir: PathLike = ".") -> Document:
    """Fetch a paper from arXiv.

    Args:
        arxiv_id: arXiv paper ID (e.g., "1706.03762" or "2301.00001v2").
        output_dir: Directory to save the PDF.

    Returns:
        Document with path, title, authors, and metadata.

    Raises:
        PaperNotFoundError: If the paper is not found.
        NetworkError: If there's a network issue.

    Example:
        >>> doc = fetch_arxiv("1706.03762", "/tmp")
        >>> print(doc.path)
        /tmp/Vaswani_2017_attention.pdf
    """
    fetcher = ArxivFetcher()
    return fetcher.fetch(arxiv_id, Path(output_dir))


def fetch_doi(doi: str, output_dir: PathLike = ".") -> Document:
    """Fetch a paper by DOI.

    Args:
        doi: DOI identifier (e.g., "10.1257/aer.20180779").
        output_dir: Directory to save the PDF.

    Returns:
        Document with path and metadata.

    Raises:
        PaperNotFoundError: If the DOI cannot be resolved.
        NetworkError: If there's a network issue.

    Example:
        >>> doc = fetch_doi("10.1257/aer.20180779", "/tmp")
    """
    fetcher = DOIFetcher()
    return fetcher.fetch(doi, Path(output_dir))


def fetch_ssrn(ssrn_id: str, output_dir: PathLike = ".") -> Document:
    """Fetch a paper from SSRN.

    Args:
        ssrn_id: SSRN paper ID.
        output_dir: Directory to save the PDF.

    Returns:
        Document with path.

    Raises:
        PaperNotFoundError: If the paper is not found.
        NetworkError: If there's a network issue.
    """
    fetcher = SSRNFetcher()
    return fetcher.fetch(ssrn_id, Path(output_dir))


def fetch_nber(nber_id: str, output_dir: PathLike = ".") -> Document:
    """Fetch a paper from NBER.

    Args:
        nber_id: NBER working paper ID (e.g., "w29000").
        output_dir: Directory to save the PDF.

    Returns:
        Document with path.

    Raises:
        PaperNotFoundError: If the paper is not found.
        NetworkError: If there's a network issue.
    """
    fetcher = NBERFetcher()
    return fetcher.fetch(nber_id, Path(output_dir))


def fetch_url(
    url: str,
    output_dir: PathLike = ".",
    name: str | None = None,
) -> Document:
    """Fetch a paper from a direct URL.

    Args:
        url: Direct URL to the PDF.
        output_dir: Directory to save the PDF.
        name: Optional custom filename (without extension).

    Returns:
        Document with path.

    Raises:
        NetworkError: If there's a network issue.
    """
    fetcher = URLFetcher()
    return fetcher.fetch(url, Path(output_dir), name=name)


def fetch_paper(identifier: str, output_dir: PathLike = ".") -> Document:
    """Auto-detect source and fetch a paper.

    Supports prefixed identifiers:
    - "arxiv:1706.03762"
    - "doi:10.1257/aer.20180779"
    - "ssrn:1234567"
    - "nber:w29000"
    - "https://..." (URLs)

    Also tries to auto-detect unprefixed identifiers.

    Args:
        identifier: Paper identifier with optional source prefix.
        output_dir: Directory to save the PDF.

    Returns:
        Document with path and metadata.

    Raises:
        ValueError: If the identifier format is not recognized.
        PaperNotFoundError: If the paper is not found.

    Example:
        >>> doc = fetch_paper("arxiv:1706.03762", "/tmp")
        >>> doc = fetch_paper("10.1257/aer.20180779", "/tmp")  # Auto-detect DOI
    """
    resolved = _resolve_identifier(identifier)
    return cast(Document, resolved.fetcher.fetch(resolved.identifier, Path(output_dir)))


async def fetch_paper_async(identifier: str, output_dir: PathLike = ".") -> Document:
    """Asynchronously fetch a paper using automatic source detection."""
    resolved = _resolve_identifier(identifier)
    return cast(Document, await resolved.fetcher.fetch_async(resolved.identifier, Path(output_dir)))


def _resolve_identifier(identifier: str):
    """Resolve the appropriate fetcher for an identifier."""
    identifier = identifier.strip()
    registry = get_registry()
    resolved = registry.resolve(identifier)
    if not resolved:
        raise ValueError(
            f"Could not determine source for identifier: {identifier}. "
            "Use a prefix like 'arxiv:', 'doi:', 'ssrn:', 'nber:', or provide a URL."
        )
    return resolved


# =============================================================================
# Extractor convenience functions
# =============================================================================


def _get_backend() -> PdfPlumberExtractor:
    """Get the default PDF extraction backend."""
    return PdfPlumberExtractor()


def extract_text(
    pdf_path: PathLike,
    pages: list[int] | None = None,
) -> str:
    """Extract text from a PDF.

    Args:
        pdf_path: Path to the PDF file.
        pages: Optional list of 0-indexed page numbers to extract.

    Returns:
        Extracted text as a string.

    Raises:
        FileNotFoundError: If the PDF doesn't exist.
        InvalidPDFError: If the file is not a valid PDF.

    Example:
        >>> text = extract_text("paper.pdf")
        >>> text = extract_text("paper.pdf", pages=[0, 1, 2])  # First 3 pages
    """
    extractor = TextExtractor(_get_backend())
    return extractor.extract(Path(pdf_path), pages=pages)


def extract_text_chunked(
    pdf_path: PathLike,
    chunk_size: int = 4000,
    overlap: int = 200,
    pages: list[int] | None = None,
) -> list[str]:
    """Extract text from a PDF as overlapping chunks.

    Useful for processing with LLMs that have context limits.

    Args:
        pdf_path: Path to the PDF file.
        chunk_size: Target size per chunk in characters.
        overlap: Overlap between chunks in characters.
        pages: Optional list of 0-indexed page numbers to extract.

    Returns:
        List of text chunks.

    Raises:
        ValueError: If overlap >= chunk_size.
        FileNotFoundError: If the PDF doesn't exist.
        InvalidPDFError: If the file is not a valid PDF.

    Example:
        >>> chunks = extract_text_chunked("paper.pdf", chunk_size=2000)
        >>> for chunk in chunks:
        ...     # Process each chunk with LLM
        ...     pass
    """
    extractor = TextExtractor(_get_backend())
    return extractor.extract_chunked(
        Path(pdf_path),
        chunk_size=chunk_size,
        overlap=overlap,
        pages=pages,
    )


def extract_tables(
    pdf_path: PathLike,
    pages: list[int] | None = None,
) -> list[ExtractedTable]:
    """Extract tables from a PDF.

    Args:
        pdf_path: Path to the PDF file.
        pages: Optional list of 0-indexed page numbers to extract from.

    Returns:
        List of ExtractedTable objects.

    Example:
        >>> tables = extract_tables("paper.pdf")
        >>> for table in tables:
        ...     print(table.to_csv())
    """
    extractor = TableExtractor(_get_backend())
    return extractor.extract(Path(pdf_path), pages=pages)


def extract_refs(pdf_path: PathLike) -> list[Reference]:
    """Extract references/bibliography from a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of Reference objects.

    Example:
        >>> refs = extract_refs("paper.pdf")
        >>> for ref in refs:
        ...     print(ref.to_bibtex())
    """
    extractor = ReferenceExtractor(_get_backend())
    return extractor.extract(Path(pdf_path))


def extract_figures(pdf_path: PathLike) -> list[ExtractedFigure]:
    """Extract figures from a PDF.

    Requires PyMuPDF: pip install pymupdf

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of ExtractedFigure objects.

    Raises:
        ImportError: If PyMuPDF is not installed.

    Example:
        >>> figures = extract_figures("paper.pdf")
        >>> figures[0].save("figure1.png")
    """
    extractor = FigureExtractor()
    return extractor.extract(Path(pdf_path))
