"""Reference/bibliography extraction logic."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from papercut.extractors.base import Extractor


@dataclass
class Reference:
    """Represents a parsed reference/citation."""

    raw_text: str
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None

    def to_bibtex(self) -> str:
        """Convert reference to BibTeX format.

        Returns:
            BibTeX entry string.
        """
        # Generate a citation key
        key = self._generate_key()
        entry_type = "article" if self.journal else "misc"

        lines = [f"@{entry_type}{{{key},"]

        if self.authors:
            author_str = " and ".join(self.authors)
            lines.append(f"  author = {{{author_str}}},")

        if self.title:
            lines.append(f"  title = {{{self.title}}},")

        if self.year:
            lines.append(f"  year = {{{self.year}}},")

        if self.journal:
            lines.append(f"  journal = {{{self.journal}}},")

        if self.volume:
            lines.append(f"  volume = {{{self.volume}}},")

        if self.pages:
            lines.append(f"  pages = {{{self.pages}}},")

        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")

        if self.url:
            lines.append(f"  url = {{{self.url}}},")

        lines.append("}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert reference to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "raw_text": self.raw_text,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "volume": self.volume,
            "pages": self.pages,
            "doi": self.doi,
            "url": self.url,
        }

    def _generate_key(self) -> str:
        """Generate a BibTeX citation key.

        Returns:
            Citation key string (e.g., 'smith2020' or 'unknown2020').
        """
        author_part = "unknown"
        if self.authors:
            # Get first author's last name
            first_author = self.authors[0]
            # Try to extract last name
            parts = first_author.replace(",", " ").split()
            if parts:
                author_part = parts[0].lower()
                # Remove non-alphanumeric
                author_part = re.sub(r"[^a-z]", "", author_part)

        year_part = str(self.year) if self.year else "0000"
        return f"{author_part}{year_part}"


class ReferenceExtractor:
    """Extract references from PDFs."""

    # Patterns for finding references section
    SECTION_PATTERNS = [
        r"(?i)^references?\s*$",
        r"(?i)^bibliography\s*$",
        r"(?i)^works?\s+cited\s*$",
        r"(?i)^literature\s+cited\s*$",
    ]

    # Pattern for DOI
    DOI_PATTERN = re.compile(r"10\.\d{4,}/[^\s]+")

    # Pattern for year in parentheses or standalone
    YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

    # Pattern for page ranges
    PAGES_PATTERN = re.compile(r"\b(\d+)\s*[-–—]\s*(\d+)\b")

    def __init__(self, backend: Extractor):
        """Initialize with an extraction backend.

        Args:
            backend: PDF extraction backend.
        """
        self.backend = backend

    def extract(self, path: Path) -> list[Reference]:
        """Extract references from PDF.

        Args:
            path: Path to the PDF file.

        Returns:
            List of Reference objects.
        """
        text = self.backend.extract_text(path)
        if not text:
            return []

        # Find references section
        refs_text = self._find_references_section(text)
        if not refs_text:
            return []

        # Split into individual references
        raw_refs = self._split_references(refs_text)

        # Parse each reference
        return [self._parse_reference(ref) for ref in raw_refs if ref.strip()]

    def _find_references_section(self, text: str) -> Optional[str]:
        """Find the references section in the text.

        Args:
            text: Full document text.

        Returns:
            References section text, or None if not found.
        """
        lines = text.split("\n")

        # Find the start of references section
        start_idx = None
        for i, line in enumerate(lines):
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, line.strip()):
                    start_idx = i + 1
                    break
            if start_idx:
                break

        if start_idx is None:
            return None

        # Take everything from the references header to the end
        # (could be improved to detect end of references)
        return "\n".join(lines[start_idx:])

    def _split_references(self, refs_text: str) -> list[str]:
        """Split references section into individual references.

        Args:
            refs_text: Text of the references section.

        Returns:
            List of individual reference strings.
        """
        # Try to split by numbered references [1], [2], etc.
        numbered = re.split(r"\n\s*\[\d+\]\s*", refs_text)
        if len(numbered) > 2:
            return [ref.strip() for ref in numbered if ref.strip()]

        # Try to split by line-based patterns (each ref on new line starting with author)
        lines = refs_text.split("\n")
        refs = []
        current_ref = []

        for line in lines:
            line = line.strip()
            if not line:
                if current_ref:
                    refs.append(" ".join(current_ref))
                    current_ref = []
                continue

            # Check if this looks like a new reference (starts with author name pattern)
            if self._looks_like_new_reference(line) and current_ref:
                refs.append(" ".join(current_ref))
                current_ref = [line]
            else:
                current_ref.append(line)

        if current_ref:
            refs.append(" ".join(current_ref))

        return refs

    def _looks_like_new_reference(self, line: str) -> bool:
        """Check if a line looks like the start of a new reference.

        Args:
            line: Text line to check.

        Returns:
            True if line appears to start a new reference.
        """
        # Starts with capital letter, possibly author name
        if not line or not line[0].isupper():
            return False

        # Contains a year early in the line
        year_match = self.YEAR_PATTERN.search(line[:80])
        return year_match is not None

    def _parse_reference(self, raw_text: str) -> Reference:
        """Parse a raw reference string into a Reference object.

        Args:
            raw_text: Raw reference text.

        Returns:
            Reference object with parsed fields.
        """
        ref = Reference(raw_text=raw_text)

        # Extract year
        year_match = self.YEAR_PATTERN.search(raw_text)
        if year_match:
            ref.year = int(year_match.group())

        # Extract DOI
        doi_match = self.DOI_PATTERN.search(raw_text)
        if doi_match:
            ref.doi = doi_match.group()

        # Extract pages
        pages_match = self.PAGES_PATTERN.search(raw_text)
        if pages_match:
            ref.pages = f"{pages_match.group(1)}-{pages_match.group(2)}"

        # Try to extract title (often in quotes or italics, or between year and journal)
        ref.title = self._extract_title(raw_text)

        # Try to extract authors (before the year typically)
        ref.authors = self._extract_authors(raw_text)

        return ref

    def _extract_title(self, text: str) -> Optional[str]:
        """Extract title from reference text.

        Args:
            text: Reference text.

        Returns:
            Extracted title or None.
        """
        # Look for quoted title
        quoted = re.search(r'"([^"]+)"', text)
        if quoted:
            return quoted.group(1)

        # Look for title between year and journal indicators
        year_match = self.YEAR_PATTERN.search(text)
        if year_match:
            after_year = text[year_match.end() :].strip()
            # Remove leading punctuation
            after_year = re.sub(r"^[.,:\s)]+", "", after_year)
            # Take until period or journal-like content
            title_match = re.match(r"([^.]+)", after_year)
            if title_match:
                title = title_match.group(1).strip()
                if len(title) > 10:
                    return title

        return None

    def _extract_authors(self, text: str) -> list[str]:
        """Extract author names from reference text.

        Args:
            text: Reference text.

        Returns:
            List of author names.
        """
        # Find text before year
        year_match = self.YEAR_PATTERN.search(text)
        if not year_match:
            return []

        author_part = text[: year_match.start()].strip()
        # Remove trailing punctuation and parentheses
        author_part = re.sub(r"[\s,.(]+$", "", author_part)

        if not author_part:
            return []

        # Split by common separators
        # Handle "and", "&", commas
        author_part = re.sub(r"\s+and\s+", ", ", author_part, flags=re.IGNORECASE)
        author_part = re.sub(r"\s*&\s*", ", ", author_part)

        authors = [a.strip() for a in author_part.split(",") if a.strip()]

        # Clean up authors (remove et al., etc.)
        authors = [a for a in authors if a.lower() not in ("et al", "et al.")]

        return authors[:10]  # Limit to reasonable number
