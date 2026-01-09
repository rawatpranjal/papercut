"""Ingestion pipeline orchestrator for Papercutter Factory.

This module provides the main IngestPipeline class that orchestrates:
1. The Sawmill (PDF splitting for large books)
2. BibTeX three-way matching
3. Docling conversion (with OCR fallback)
4. Fetching missing papers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from papercutter.ingest.docling_wrapper import DoclingResult, DoclingWrapper
from papercutter.ingest.fetchers import FetcherRegistry, get_registry
from papercutter.ingest.matcher import (
    BibTeXMatcher,
    MatchedPaper,
    MatchResult,
    MatchType,
    parse_bibtex_file,
)
from papercutter.ingest.ocr_fallback import OCRFallback, OCRResult
from papercutter.ingest.splitter import Chapter, Splitter, SplitResult
from papercutter.project.inventory import (
    ExtractionMethod as InventoryExtractionMethod,
    PaperEntry,
    PaperStatus,
)
from papercutter.utils.bibtex import BibTeXEntry
from papercutter.utils.hashing import compute_file_hash

logger = logging.getLogger(__name__)


class ExtractionMethod(str, Enum):
    """Method used to extract content from PDF."""

    DOCLING = "docling"
    OCR_FALLBACK = "ocr_fallback"
    FAILED = "failed"


@dataclass
class IngestProgress:
    """Progress update during ingestion."""

    stage: str  # "sawmill", "matching", "conversion", "fetching"
    current: int
    total: int
    message: str
    paper_id: str | None = None


@dataclass
class IngestResult:
    """Result of the ingestion pipeline."""

    entries: list[PaperEntry] = field(default_factory=list)
    """All paper entries created."""

    split_results: list[SplitResult] = field(default_factory=list)
    """Results from the Sawmill (PDF splitting)."""

    match_result: MatchResult | None = None
    """Result from BibTeX matching."""

    fetched_papers: list[Path] = field(default_factory=list)
    """Papers fetched from remote sources."""

    failed_fetches: list[tuple[str, str]] = field(default_factory=list)
    """Failed fetches: (identifier, error_message)."""

    conversion_results: dict[str, str] = field(default_factory=dict)
    """Map of paper_id -> extraction_method."""

    errors: list[tuple[str, str]] = field(default_factory=list)
    """Errors: (context, message)."""


class IngestPipeline:
    """Main ingestion pipeline for Papercutter Factory.

    Orchestrates the full ingestion workflow:
    1. Sawmill: Detect and split large books (500+ pages)
    2. Matching: Three-way BibTeX matching
    3. Conversion: Docling with OCR fallback
    4. Fetching: Download papers for bib-only entries

    Example:
        pipeline = IngestPipeline()
        result = pipeline.ingest(
            pdf_dir=Path("papers/"),
            bib_file=Path("references.bib"),
            output_dir=Path(".papercutter/"),
        )
    """

    def __init__(
        self,
        split_threshold: int = 500,
        docling_enabled: bool = True,
        fetch_missing: bool = True,
        progress_callback: Callable[[IngestProgress], None] | None = None,
    ):
        """Initialize the pipeline.

        Args:
            split_threshold: Page threshold for splitting large PDFs.
            docling_enabled: Use Docling for conversion (falls back to OCR if fails).
            fetch_missing: Fetch papers for bib-only entries.
            progress_callback: Optional callback for progress updates.
        """
        self.split_threshold = split_threshold
        self.docling_enabled = docling_enabled
        self.fetch_missing = fetch_missing
        self.progress_callback = progress_callback

        # Initialize components
        self.splitter = Splitter(split_threshold_pages=split_threshold)
        self.matcher = BibTeXMatcher()
        self.docling = DoclingWrapper() if docling_enabled else None
        self.ocr_fallback = OCRFallback()
        self.fetcher_registry = get_registry()

    def ingest(
        self,
        pdf_dir: Path | None = None,
        pdf_files: list[Path] | None = None,
        bib_file: Path | None = None,
        output_dir: Path | None = None,
    ) -> IngestResult:
        """Run the full ingestion pipeline.

        Args:
            pdf_dir: Directory containing PDF files.
            pdf_files: Explicit list of PDF files (alternative to pdf_dir).
            bib_file: Optional BibTeX file for matching.
            output_dir: Output directory for processed files.

        Returns:
            IngestResult with all processing results.
        """
        result = IngestResult()

        # Collect PDF files
        if pdf_files:
            pdfs = [Path(p) for p in pdf_files]
        elif pdf_dir:
            pdf_dir = Path(pdf_dir)
            pdfs = list(pdf_dir.glob("**/*.pdf"))
        else:
            return result

        if not pdfs:
            logger.warning("No PDF files found")
            return result

        # Set output directory
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            markdown_dir = output_dir / "markdown"
            markdown_dir.mkdir(exist_ok=True)
            chunks_dir = output_dir / "chunks"
            chunks_dir.mkdir(exist_ok=True)
        else:
            markdown_dir = None
            chunks_dir = None

        # Stage 1: Sawmill (split large PDFs)
        self._report_progress("sawmill", 0, len(pdfs), "Checking for large PDFs...")
        processed_pdfs, split_results = self._run_sawmill(pdfs, chunks_dir, result)
        result.split_results = split_results

        # Stage 2: BibTeX matching
        bib_entries = []
        if bib_file and bib_file.exists():
            self._report_progress("matching", 0, 1, f"Parsing {bib_file.name}...")
            bib_entries = parse_bibtex_file(bib_file)

        pdf_metadata = self._extract_metadata_for_matching(processed_pdfs)
        self._report_progress("matching", 0, len(pdf_metadata), "Matching PDFs to BibTeX...")
        result.match_result = self.matcher.match(bib_entries, pdf_metadata)

        # Stage 3: Fetch missing papers (bib-only)
        if self.fetch_missing and result.match_result and output_dir:
            self._run_fetching(result.match_result.bib_only, output_dir, result)

        # Stage 4: Convert PDFs to Markdown
        all_papers = self._collect_papers_for_conversion(result.match_result, processed_pdfs)
        self._run_conversion(all_papers, markdown_dir, result)

        return result

    def _run_sawmill(
        self,
        pdfs: list[Path],
        chunks_dir: Path | None,
        result: IngestResult,
    ) -> tuple[list[Path], list[SplitResult]]:
        """Run the Sawmill to split large PDFs."""
        processed_pdfs: list[Path] = []
        split_results: list[SplitResult] = []

        for i, pdf in enumerate(pdfs):
            self._report_progress(
                "sawmill", i + 1, len(pdfs), f"Checking {pdf.name}..."
            )

            try:
                if self.splitter.should_split(pdf):
                    logger.info(f"Splitting large PDF: {pdf.name}")

                    if chunks_dir:
                        split_dir = chunks_dir / pdf.stem
                    else:
                        split_dir = pdf.parent / f"{pdf.stem}_chunks"

                    split_result = self.splitter.split_pdf(pdf, split_dir)
                    split_results.append(split_result)

                    # Add chunk paths to processed list
                    for chunk_path, _ in split_result.chunks:
                        processed_pdfs.append(chunk_path)
                else:
                    processed_pdfs.append(pdf)

            except Exception as e:
                logger.error(f"Failed to process {pdf.name}: {e}")
                result.errors.append((f"sawmill:{pdf.name}", str(e)))
                # Still include the original PDF
                processed_pdfs.append(pdf)

        return processed_pdfs, split_results

    def _extract_metadata_for_matching(
        self, pdfs: list[Path]
    ) -> list[dict[str, Any]]:
        """Extract basic metadata from PDFs for matching.

        This is a lightweight extraction just for matching purposes.
        Full conversion happens later.
        """
        metadata_list = []

        for pdf in pdfs:
            metadata: dict[str, Any] = {
                "path": str(pdf),
                "title": None,
                "authors": [],
                "doi": None,
                "arxiv_id": None,
            }

            try:
                # Quick text extraction for title
                text = self._extract_first_page_text(pdf)
                if text:
                    metadata["title"] = self._guess_title_from_text(text)
                    metadata["doi"] = self._extract_doi_from_text(text)
                    metadata["arxiv_id"] = self._extract_arxiv_from_text(text)
            except Exception as e:
                logger.debug(f"Metadata extraction failed for {pdf.name}: {e}")

            metadata_list.append(metadata)

        return metadata_list

    def _extract_first_page_text(self, pdf_path: Path) -> str:
        """Extract text from first page for quick metadata."""
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                if pdf.pages:
                    return pdf.pages[0].extract_text() or ""
        except Exception:
            pass
        return ""

    def _guess_title_from_text(self, text: str) -> str | None:
        """Guess title from first page text."""
        lines = text.strip().split("\n")
        for line in lines[:10]:
            line = line.strip()
            # Skip short lines, numbers, page markers
            if len(line) > 15 and len(line) < 200:
                if not line.isdigit():
                    return line
        return None

    def _extract_doi_from_text(self, text: str) -> str | None:
        """Extract DOI from text."""
        import re

        match = re.search(r"10\.\d{4,}/[^\s]+", text)
        if match:
            return match.group()
        return None

    def _extract_arxiv_from_text(self, text: str) -> str | None:
        """Extract arXiv ID from text."""
        import re

        # Modern format: 2301.00001
        match = re.search(r"\d{4}\.\d{4,5}", text)
        if match:
            return match.group()
        # Old format: hep-th/9901001
        match = re.search(r"[a-z\-]+/\d{7}", text, re.IGNORECASE)
        if match:
            return match.group()
        return None

    def _run_fetching(
        self,
        bib_only: list[MatchedPaper],
        output_dir: Path,
        result: IngestResult,
    ) -> None:
        """Fetch papers for bib-only entries."""
        fetch_dir = output_dir / "fetched"
        fetch_dir.mkdir(exist_ok=True)

        for i, paper in enumerate(bib_only):
            self._report_progress(
                "fetching",
                i + 1,
                len(bib_only),
                f"Fetching {paper.bibtex_key}...",
            )

            identifier = paper.doi or paper.arxiv_id
            if not identifier:
                result.failed_fetches.append(
                    (paper.bibtex_key or "unknown", "No DOI or arXiv ID")
                )
                continue

            try:
                doc = self.fetcher_registry.fetch(identifier, fetch_dir)
                result.fetched_papers.append(doc.path)
                paper.pdf_path = doc.path
                paper.match_type = MatchType.MATCHED
                logger.info(f"Fetched: {doc.path.name}")

            except Exception as e:
                logger.warning(f"Failed to fetch {identifier}: {e}")
                result.failed_fetches.append((identifier, str(e)))

    def _collect_papers_for_conversion(
        self,
        match_result: MatchResult | None,
        processed_pdfs: list[Path],
    ) -> list[Path]:
        """Collect all PDFs that need conversion."""
        if match_result:
            paths = set()
            for paper in match_result.matched:
                if paper.pdf_path:
                    paths.add(paper.pdf_path)
            for paper in match_result.pdf_only:
                if paper.pdf_path:
                    paths.add(paper.pdf_path)
            return list(paths)
        return processed_pdfs

    def _run_conversion(
        self,
        pdfs: list[Path],
        markdown_dir: Path | None,
        result: IngestResult,
    ) -> None:
        """Convert PDFs to Markdown using Docling with OCR fallback."""
        for i, pdf in enumerate(pdfs):
            self._report_progress(
                "conversion",
                i + 1,
                len(pdfs),
                f"Converting {pdf.name}...",
            )

            paper_id = compute_file_hash(pdf)
            method = ExtractionMethod.FAILED

            # Try Docling first
            if self.docling and DoclingWrapper.is_available():
                try:
                    docling_result = self.docling.convert(pdf)
                    method = ExtractionMethod.DOCLING

                    if markdown_dir:
                        md_path = markdown_dir / f"{pdf.stem}.md"
                        md_path.write_text(docling_result.markdown)

                    # Create paper entry
                    entry = PaperEntry(
                        id=paper_id,
                        filename=pdf.name,
                        path=str(pdf),
                        title=docling_result.title,
                        authors=docling_result.authors,
                        status=PaperStatus.INGESTED,
                        markdown_path=str(md_path) if markdown_dir else None,
                        extraction_method=InventoryExtractionMethod.DOCLING,
                    )
                    result.entries.append(entry)
                    result.conversion_results[paper_id] = method.value
                    continue

                except Exception as e:
                    logger.warning(f"Docling failed for {pdf.name}: {e}")

            # Fall back to OCR
            try:
                ocr_result = self.ocr_fallback.extract(pdf)
                method = ExtractionMethod.OCR_FALLBACK

                if markdown_dir:
                    md_path = markdown_dir / f"{pdf.stem}.md"
                    md_path.write_text(ocr_result.markdown)

                entry = PaperEntry(
                    id=paper_id,
                    filename=pdf.name,
                    path=str(pdf),
                    title=ocr_result.title,
                    status=PaperStatus.INGESTED,
                    markdown_path=str(md_path) if markdown_dir else None,
                    extraction_method=InventoryExtractionMethod.OCR_FALLBACK,
                )
                result.entries.append(entry)
                result.conversion_results[paper_id] = method.value

            except Exception as e:
                logger.error(f"OCR fallback failed for {pdf.name}: {e}")
                result.errors.append((f"conversion:{pdf.name}", str(e)))
                result.conversion_results[paper_id] = ExtractionMethod.FAILED.value

                # Still create an entry for tracking
                entry = PaperEntry(
                    id=paper_id,
                    filename=pdf.name,
                    path=str(pdf),
                    status=PaperStatus.FAILED,
                    extraction_method=None,
                )
                result.entries.append(entry)

    def _report_progress(
        self,
        stage: str,
        current: int,
        total: int,
        message: str,
        paper_id: str | None = None,
    ) -> None:
        """Report progress via callback if available."""
        if self.progress_callback:
            progress = IngestProgress(
                stage=stage,
                current=current,
                total=total,
                message=message,
                paper_id=paper_id,
            )
            self.progress_callback(progress)
