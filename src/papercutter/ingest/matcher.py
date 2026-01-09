"""BibTeX three-way matcher for aligning PDFs with bibliography entries.

This module handles three scenarios:
1. Bib + PDF: Fuzzy match PDF title/metadata to bib entry
2. Bib only: Use fetchers to download PDF from DOI/arXiv
3. PDF only: Generate temporary bib entry from extracted metadata
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from papercutter.utils.bibtex import BibTeXEntry

logger = logging.getLogger(__name__)


class MatchType(str, Enum):
    """Type of match between BibTeX and PDF."""

    MATCHED = "matched"  # PDF fuzzy-matched to bib entry
    BIB_ONLY = "bib_only"  # Bib entry without PDF (needs fetch)
    PDF_ONLY = "pdf_only"  # PDF without bib entry (generated temp entry)
    UNMATCHED = "unmatched"  # Failed to match or fetch


@dataclass
class MatchedPaper:
    """A paper with its matching status and metadata."""

    match_type: MatchType

    # PDF info (may be None for BIB_ONLY before fetch)
    pdf_path: Path | None = None
    pdf_title: str | None = None
    pdf_authors: list[str] = field(default_factory=list)

    # BibTeX info (may be None for PDF_ONLY)
    bibtex_key: str | None = None
    bibtex_entry: BibTeXEntry | None = None

    # Matching metadata
    match_score: float = 0.0  # 0-100 fuzzy match score
    match_method: str = ""  # e.g., "title", "doi", "arxiv"

    # Identifiers for fetching (BIB_ONLY)
    doi: str | None = None
    arxiv_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "match_type": self.match_type.value,
            "pdf_path": str(self.pdf_path) if self.pdf_path else None,
            "pdf_title": self.pdf_title,
            "pdf_authors": self.pdf_authors,
            "bibtex_key": self.bibtex_key,
            "match_score": self.match_score,
            "match_method": self.match_method,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
        }


@dataclass
class MatchResult:
    """Result of the three-way matching process."""

    matched: list[MatchedPaper] = field(default_factory=list)
    """Papers with successful bib-PDF matches."""

    bib_only: list[MatchedPaper] = field(default_factory=list)
    """Bib entries without PDFs (need fetching)."""

    pdf_only: list[MatchedPaper] = field(default_factory=list)
    """PDFs without bib entries (generated temp entries)."""

    failed: list[MatchedPaper] = field(default_factory=list)
    """Failed matches or fetches."""

    @property
    def total(self) -> int:
        """Total number of papers processed."""
        return len(self.matched) + len(self.bib_only) + len(self.pdf_only) + len(self.failed)


class BibTeXMatcher:
    """Three-way matcher for BibTeX entries and PDF files.

    Handles:
    1. Matching existing PDFs to BibTeX entries using fuzzy matching
    2. Identifying BibTeX entries that need PDFs fetched (via DOI/arXiv)
    3. Creating temporary BibTeX entries for orphan PDFs
    """

    # Minimum score for a title match to be considered valid
    MIN_MATCH_SCORE = 70

    def __init__(
        self,
        min_match_score: int = 70,
        match_on_doi: bool = True,
        match_on_arxiv: bool = True,
    ):
        """Initialize the matcher.

        Args:
            min_match_score: Minimum fuzzy match score (0-100) for title matching.
            match_on_doi: Also match by DOI if available.
            match_on_arxiv: Also match by arXiv ID if available.
        """
        self.min_match_score = min_match_score
        self.match_on_doi = match_on_doi
        self.match_on_arxiv = match_on_arxiv
        self._fuzz = None  # Lazy load

    def _get_fuzz(self):
        """Lazy load thefuzz library."""
        if self._fuzz is None:
            try:
                from thefuzz import fuzz

                self._fuzz = fuzz
            except ImportError:
                logger.warning(
                    "thefuzz not installed, using simple matching. "
                    "Install with: pip install thefuzz"
                )
                self._fuzz = False  # Flag that it's unavailable
        return self._fuzz

    def match(
        self,
        bib_entries: list[BibTeXEntry],
        pdf_metadata: list[dict[str, Any]],
    ) -> MatchResult:
        """Perform three-way matching between BibTeX entries and PDF metadata.

        Args:
            bib_entries: List of BibTeX entries from .bib file.
            pdf_metadata: List of dicts with PDF info:
                - path: Path to PDF file
                - title: Extracted title (optional)
                - authors: List of authors (optional)
                - doi: DOI if found in PDF (optional)
                - arxiv_id: arXiv ID if found (optional)

        Returns:
            MatchResult with categorized papers.
        """
        result = MatchResult()

        # Track which items have been matched
        matched_bib_keys: set[str] = set()
        matched_pdf_paths: set[Path] = set()

        # First pass: Try to match by identifiers (DOI, arXiv)
        if self.match_on_doi or self.match_on_arxiv:
            self._match_by_identifiers(
                bib_entries,
                pdf_metadata,
                matched_bib_keys,
                matched_pdf_paths,
                result,
            )

        # Second pass: Fuzzy match by title
        self._match_by_title(
            bib_entries,
            pdf_metadata,
            matched_bib_keys,
            matched_pdf_paths,
            result,
        )

        # Handle unmatched bib entries (bib-only)
        for entry in bib_entries:
            if entry.key not in matched_bib_keys:
                paper = MatchedPaper(
                    match_type=MatchType.BIB_ONLY,
                    bibtex_key=entry.key,
                    bibtex_entry=entry,
                    doi=entry.doi,
                    arxiv_id=entry.arxiv_id,
                )
                result.bib_only.append(paper)

        # Handle unmatched PDFs (pdf-only)
        for pdf_info in pdf_metadata:
            pdf_path = Path(pdf_info.get("path", ""))
            if pdf_path not in matched_pdf_paths:
                # Generate temporary bib entry
                temp_entry = self._generate_temp_bibtex(pdf_info)
                paper = MatchedPaper(
                    match_type=MatchType.PDF_ONLY,
                    pdf_path=pdf_path,
                    pdf_title=pdf_info.get("title"),
                    pdf_authors=pdf_info.get("authors", []),
                    bibtex_key=temp_entry.key,
                    bibtex_entry=temp_entry,
                    match_method="generated",
                )
                result.pdf_only.append(paper)

        return result

    def _match_by_identifiers(
        self,
        bib_entries: list[BibTeXEntry],
        pdf_metadata: list[dict[str, Any]],
        matched_bib_keys: set[str],
        matched_pdf_paths: set[Path],
        result: MatchResult,
    ) -> None:
        """Match by DOI or arXiv ID."""
        # Build lookup maps for identifiers
        bib_by_doi: dict[str, BibTeXEntry] = {}
        bib_by_arxiv: dict[str, BibTeXEntry] = {}

        for entry in bib_entries:
            if entry.doi and self.match_on_doi:
                bib_by_doi[self._normalize_doi(entry.doi)] = entry
            if entry.arxiv_id and self.match_on_arxiv:
                bib_by_arxiv[self._normalize_arxiv(entry.arxiv_id)] = entry

        # Try to match each PDF by identifier
        for pdf_info in pdf_metadata:
            pdf_path = Path(pdf_info.get("path", ""))

            # Try DOI match
            pdf_doi = pdf_info.get("doi")
            if pdf_doi and self.match_on_doi:
                normalized_doi = self._normalize_doi(pdf_doi)
                if normalized_doi in bib_by_doi:
                    entry = bib_by_doi[normalized_doi]
                    if entry.key not in matched_bib_keys:
                        self._add_match(
                            result,
                            entry,
                            pdf_info,
                            score=100.0,
                            method="doi",
                        )
                        matched_bib_keys.add(entry.key)
                        matched_pdf_paths.add(pdf_path)
                        continue

            # Try arXiv match
            pdf_arxiv = pdf_info.get("arxiv_id")
            if pdf_arxiv and self.match_on_arxiv:
                normalized_arxiv = self._normalize_arxiv(pdf_arxiv)
                if normalized_arxiv in bib_by_arxiv:
                    entry = bib_by_arxiv[normalized_arxiv]
                    if entry.key not in matched_bib_keys:
                        self._add_match(
                            result,
                            entry,
                            pdf_info,
                            score=100.0,
                            method="arxiv",
                        )
                        matched_bib_keys.add(entry.key)
                        matched_pdf_paths.add(pdf_path)
                        continue

    def _match_by_title(
        self,
        bib_entries: list[BibTeXEntry],
        pdf_metadata: list[dict[str, Any]],
        matched_bib_keys: set[str],
        matched_pdf_paths: set[Path],
        result: MatchResult,
    ) -> None:
        """Match by fuzzy title comparison."""
        fuzz = self._get_fuzz()

        # Get unmatched items
        unmatched_bibs = [e for e in bib_entries if e.key not in matched_bib_keys]
        unmatched_pdfs = [
            p for p in pdf_metadata if Path(p.get("path", "")) not in matched_pdf_paths
        ]

        # For each unmatched PDF, find best matching bib entry
        for pdf_info in unmatched_pdfs:
            pdf_path = Path(pdf_info.get("path", ""))
            pdf_title = pdf_info.get("title", "")

            if not pdf_title:
                continue

            best_match: tuple[BibTeXEntry | None, float] = (None, 0.0)

            for entry in unmatched_bibs:
                if entry.key in matched_bib_keys:
                    continue

                if not entry.title:
                    continue

                score = self._compute_title_similarity(pdf_title, entry.title, fuzz)

                if score > best_match[1]:
                    best_match = (entry, score)

            # Check if best match exceeds threshold
            if best_match[0] and best_match[1] >= self.min_match_score:
                entry = best_match[0]
                self._add_match(
                    result,
                    entry,
                    pdf_info,
                    score=best_match[1],
                    method="title",
                )
                matched_bib_keys.add(entry.key)
                matched_pdf_paths.add(pdf_path)

    def _compute_title_similarity(
        self,
        title1: str,
        title2: str,
        fuzz: Any,
    ) -> float:
        """Compute similarity score between two titles."""
        # Normalize titles
        t1 = self._normalize_title(title1)
        t2 = self._normalize_title(title2)

        if not t1 or not t2:
            return 0.0

        # Exact match
        if t1 == t2:
            return 100.0

        # Use fuzzy matching if available
        if fuzz:
            # Use token_sort_ratio for word-order independence
            return float(fuzz.token_sort_ratio(t1, t2))

        # Simple fallback: Jaccard similarity on words
        words1 = set(t1.split())
        words2 = set(t2.split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return (intersection / union) * 100

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        # Lowercase
        title = title.lower()
        # Remove punctuation
        title = re.sub(r"[^\w\s]", " ", title)
        # Normalize whitespace
        title = " ".join(title.split())
        return title

    def _normalize_doi(self, doi: str) -> str:
        """Normalize DOI for comparison."""
        doi = doi.strip().lower()
        # Remove common prefixes
        for prefix in ["doi:", "https://doi.org/", "http://doi.org/", "doi.org/"]:
            if doi.startswith(prefix):
                doi = doi[len(prefix) :]
        return doi

    def _normalize_arxiv(self, arxiv_id: str) -> str:
        """Normalize arXiv ID for comparison."""
        arxiv_id = arxiv_id.strip().lower()
        # Remove common prefixes
        for prefix in ["arxiv:", "https://arxiv.org/abs/", "http://arxiv.org/abs/"]:
            if arxiv_id.startswith(prefix):
                arxiv_id = arxiv_id[len(prefix) :]
        # Remove version suffix
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
        return arxiv_id

    def _add_match(
        self,
        result: MatchResult,
        entry: BibTeXEntry,
        pdf_info: dict[str, Any],
        score: float,
        method: str,
    ) -> None:
        """Add a successful match to the result."""
        paper = MatchedPaper(
            match_type=MatchType.MATCHED,
            pdf_path=Path(pdf_info.get("path", "")),
            pdf_title=pdf_info.get("title"),
            pdf_authors=pdf_info.get("authors", []),
            bibtex_key=entry.key,
            bibtex_entry=entry,
            match_score=score,
            match_method=method,
            doi=entry.doi or pdf_info.get("doi"),
            arxiv_id=entry.arxiv_id or pdf_info.get("arxiv_id"),
        )
        result.matched.append(paper)

    def _generate_temp_bibtex(self, pdf_info: dict[str, Any]) -> BibTeXEntry:
        """Generate a temporary BibTeX entry for an orphan PDF."""
        title = pdf_info.get("title", "")
        authors = pdf_info.get("authors", [])
        year = pdf_info.get("year")

        # Try to extract year from filename if not provided
        if not year:
            path = Path(pdf_info.get("path", ""))
            year_match = re.search(r"(19|20)\d{2}", path.stem)
            if year_match:
                year = int(year_match.group())

        entry = BibTeXEntry(
            entry_type="misc",
            title=title or Path(pdf_info.get("path", "unknown")).stem,
            authors=authors,
            year=year,
            doi=pdf_info.get("doi"),
            arxiv_id=pdf_info.get("arxiv_id"),
        )

        # Generate a key
        entry.key = entry._generate_key()

        return entry


def parse_bibtex_file(bib_path: Path) -> list[BibTeXEntry]:
    """Parse a BibTeX file into BibTeXEntry objects.

    Args:
        bib_path: Path to .bib file.

    Returns:
        List of BibTeXEntry objects.
    """
    try:
        import bibtexparser
        from bibtexparser.bparser import BibTexParser

        with open(bib_path, encoding="utf-8") as f:
            parser = BibTexParser(common_strings=True)
            bib_database = bibtexparser.load(f, parser)

        entries = []
        for entry in bib_database.entries:
            # Parse authors
            authors_str = entry.get("author", "")
            if authors_str:
                authors = [a.strip() for a in authors_str.split(" and ")]
            else:
                authors = []

            # Parse year
            year = None
            year_str = entry.get("year", "")
            if year_str:
                try:
                    year = int(year_str)
                except ValueError:
                    pass

            bib_entry = BibTeXEntry(
                entry_type=entry.get("ENTRYTYPE", "misc"),
                key=entry.get("ID", ""),
                title=entry.get("title", "").strip("{}"),
                authors=authors,
                year=year,
                journal=entry.get("journal"),
                booktitle=entry.get("booktitle"),
                publisher=entry.get("publisher"),
                volume=entry.get("volume"),
                number=entry.get("number"),
                pages=entry.get("pages"),
                doi=entry.get("doi"),
                arxiv_id=entry.get("eprint"),
                url=entry.get("url"),
                abstract=entry.get("abstract"),
            )
            entries.append(bib_entry)

        return entries

    except ImportError:
        raise ImportError(
            "bibtexparser is required for BibTeX parsing. "
            "Install with: pip install bibtexparser"
        )
