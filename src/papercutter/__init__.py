"""Papercutter: Extract knowledge from academic papers.

This module provides a comprehensive Python API for:
- Fetching papers from arXiv, DOI, SSRN, NBER, and URLs
- Extracting text, tables, figures, and references from PDFs
- Document indexing and structure detection
- LLM-powered intelligence features (summarization, reports, study aids)

Simple API (recommended for most users):
    >>> from papercutter import fetch_arxiv, extract_text
    >>>
    >>> # Fetch and extract in two lines
    >>> doc = fetch_arxiv("1706.03762", "./papers")
    >>> text = extract_text(doc.path)

Advanced usage (for more control):
    >>> from papercutter import ArxivFetcher, PdfPlumberExtractor, TextExtractor
    >>> from pathlib import Path
    >>>
    >>> # Fetch a paper
    >>> fetcher = ArxivFetcher()
    >>> doc = fetcher.fetch("1706.03762", Path("./papers"))
    >>>
    >>> # Extract text
    >>> backend = PdfPlumberExtractor()
    >>> extractor = TextExtractor(backend)
    >>> text = extractor.extract(doc.path)
"""

__version__ = "1.1.0"

# Exceptions
# Convenience API
from papercutter.api import (
    extract_figures,
    extract_refs,
    extract_tables,
    extract_text,
    extract_text_chunked,
    fetch_arxiv,
    fetch_doi,
    fetch_nber,
    fetch_paper,
    fetch_ssrn,
    fetch_url,
)

# Book chapter detection
from papercutter.books.splitter import Chapter, ChapterSplitter

# Cache
from papercutter.cache import CacheStore, file_hash, get_cache

# Configuration
from papercutter.config.settings import Settings, get_settings

# Core extraction
from papercutter.core.equations import (
    EquationExtractor,
    EquationType,
    ExtractedEquation,
    LaTeXConversion,
)
from papercutter.core.figures import ExtractedFigure, FigureExtractor
from papercutter.core.references import Reference, ReferenceExtractor
from papercutter.core.tables import ExtractedTable, TableExtractor
from papercutter.core.text import TextExtractor
from papercutter.exceptions import (
    ConfigError,
    EquationConversionError,
    EquationExtractionError,
    ExtractionError,
    FetchError,
    InvalidPDFError,
    LLMError,
    LLMNotAvailableError,
    MathPixAPIError,
    MissingAPIKeyError,
    NetworkError,
    NoContentError,
    PapercutterError,
    PaperNotFoundError,
    RateLimitError,
)

# Extractors (backends)
from papercutter.extractors.base import Extractor
from papercutter.extractors.pdfplumber import PdfPlumberExtractor

# Fetchers
from papercutter.fetchers.arxiv import ArxivFetcher
from papercutter.fetchers.base import BaseFetcher, Document
from papercutter.fetchers.doi import DOIFetcher
from papercutter.fetchers.nber import NBERFetcher
from papercutter.fetchers.ssrn import SSRNFetcher
from papercutter.fetchers.url import URLFetcher

# Document indexing
from papercutter.index.indexer import (
    DocumentIndex,
    DocumentIndexer,
    FigureInfo,
    Section,
    TableInfo,
)

# Intelligence features (LLM-powered)
from papercutter.intelligence import ReportGenerator, StudyAid, Summarizer

# LLM integration
from papercutter.llm import LLMClient
from papercutter.llm import get_client as get_llm_client
from papercutter.llm.client import LLMResponse

# Output formatting
from papercutter.output import OutputFormatter, get_formatter

__all__ = [
    # Version
    "__version__",
    # Exceptions
    "PapercutterError",
    "FetchError",
    "PaperNotFoundError",
    "RateLimitError",
    "NetworkError",
    "ExtractionError",
    "InvalidPDFError",
    "NoContentError",
    "ConfigError",
    "MissingAPIKeyError",
    "LLMError",
    "LLMNotAvailableError",
    "EquationExtractionError",
    "EquationConversionError",
    "MathPixAPIError",
    # Fetchers
    "BaseFetcher",
    "Document",
    "ArxivFetcher",
    "DOIFetcher",
    "SSRNFetcher",
    "NBERFetcher",
    "URLFetcher",
    # Extractors
    "Extractor",
    "PdfPlumberExtractor",
    # Core extraction
    "TextExtractor",
    "TableExtractor",
    "ExtractedTable",
    "ReferenceExtractor",
    "Reference",
    "FigureExtractor",
    "ExtractedFigure",
    "EquationExtractor",
    "ExtractedEquation",
    "EquationType",
    "LaTeXConversion",
    # Document indexing
    "DocumentIndexer",
    "DocumentIndex",
    "Section",
    "TableInfo",
    "FigureInfo",
    # Books
    "ChapterSplitter",
    "Chapter",
    # Cache
    "CacheStore",
    "get_cache",
    "file_hash",
    # Configuration
    "Settings",
    "get_settings",
    # Output
    "OutputFormatter",
    "get_formatter",
    # LLM
    "LLMClient",
    "LLMResponse",
    "get_llm_client",
    # Intelligence
    "Summarizer",
    "ReportGenerator",
    "StudyAid",
    # Convenience API
    "fetch_arxiv",
    "fetch_doi",
    "fetch_ssrn",
    "fetch_nber",
    "fetch_url",
    "fetch_paper",
    "extract_text",
    "extract_text_chunked",
    "extract_tables",
    "extract_refs",
    "extract_figures",
]
