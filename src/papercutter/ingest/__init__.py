"""Ingestion pipeline for Papercutter Factory.

This module handles the complete paper ingestion workflow:
1. PDF splitting (Sawmill) for large books
2. BibTeX matching (three-way: Bib+PDF, Bib-only, PDF-only)
3. PDF to Markdown conversion (Docling with OCR fallback)
4. Fetching papers from academic sources
"""

from papercutter.ingest.docling_wrapper import (
    DoclingResult,
    DoclingWrapper,
    ExtractedTable,
    convert_pdf,
)
from papercutter.ingest.fetchers import (
    BaseFetcher,
    Document,
    FetcherRegistry,
    ResolvedIdentifier,
    get_registry,
)
from papercutter.ingest.matcher import (
    BibTeXMatcher,
    MatchedPaper,
    MatchResult,
    MatchType,
    parse_bibtex_file,
)
from papercutter.ingest.ocr_fallback import (
    OCRFallback,
    OCRResult,
    OCRTable,
    extract_with_fallback,
)
from papercutter.ingest.pipeline import (
    ExtractionMethod,
    IngestPipeline,
    IngestProgress,
    IngestResult,
)
from papercutter.ingest.splitter import Chapter, Splitter, SplitResult

__all__ = [
    # Fetchers
    "BaseFetcher",
    "Document",
    "FetcherRegistry",
    "ResolvedIdentifier",
    "get_registry",
    # Splitter (Sawmill)
    "Chapter",
    "Splitter",
    "SplitResult",
    # Docling wrapper
    "DoclingWrapper",
    "DoclingResult",
    "ExtractedTable",
    "convert_pdf",
    # OCR fallback
    "OCRFallback",
    "OCRResult",
    "OCRTable",
    "extract_with_fallback",
    # BibTeX matcher
    "BibTeXMatcher",
    "MatchedPaper",
    "MatchResult",
    "MatchType",
    "parse_bibtex_file",
    # Pipeline
    "IngestPipeline",
    "IngestProgress",
    "IngestResult",
    "ExtractionMethod",
]
