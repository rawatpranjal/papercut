"""Reference/bibliography extraction logic."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from papercutter.extractors.base import Extractor


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
            Citation key string (e.g., 'vaswani2017attention').
        """
        author_part = self._extract_last_name(self.authors[0]) if self.authors else "unknown"
        year_part = str(self.year) if self.year else "0000"
        title_part = self._extract_title_word(self.title) if self.title else ""

        return f"{author_part}{year_part}{title_part}"

    def _extract_last_name(self, author: str) -> str:
        """Extract last name from author string.

        Handles formats like:
        - "Smith, John" -> "smith"
        - "John Smith" -> "smith"
        - "van der Berg, Jan" -> "vandenberg"
        - "Smith-Jones, Mary" -> "smithjones"

        Args:
            author: Author name string.

        Returns:
            Lowercase last name suitable for citation key.
        """
        author = author.strip()
        if not author:
            return "unknown"

        # Name particles that should be included in last name
        particles = {"van", "von", "de", "del", "della", "der", "den", "la", "le", "di"}

        # Check for "Last, First" format
        if "," in author:
            last_name = author.split(",")[0].strip()
        else:
            # "First Last" format - take everything after first name
            parts = author.split()
            if len(parts) == 1:
                last_name = parts[0]
            else:
                # Find where last name starts (may include particles)
                last_name_parts = []
                for i, part in enumerate(parts):
                    part_lower = part.lower().rstrip(".")
                    if part_lower in particles:
                        # Start collecting from here
                        last_name_parts = parts[i:]
                        break
                if not last_name_parts:
                    # No particles found, take last word
                    last_name = parts[-1]
                else:
                    last_name = " ".join(last_name_parts)

        # Normalize: lowercase, remove hyphens and non-alpha characters
        last_name = last_name.lower()
        last_name = re.sub(r"[^a-z]", "", last_name)

        return last_name if last_name else "unknown"

    def _extract_title_word(self, title: str) -> str:
        """Extract first significant word from title.

        Skips common words like articles and prepositions.

        Args:
            title: Paper title.

        Returns:
            Lowercase first significant word.
        """
        if not title:
            return ""

        # Common words to skip
        skip_words = {
            "a", "an", "the", "on", "in", "of", "for", "to", "and", "or",
            "with", "by", "from", "at", "is", "are", "was", "were", "be",
            "this", "that", "these", "those", "how", "what", "why", "when",
        }

        # Split title into words
        words = re.findall(r"[a-zA-Z]+", title)

        for word in words:
            word_lower = word.lower()
            if word_lower not in skip_words and len(word_lower) > 1:
                return word_lower

        # Fallback to first word if all are skip words
        return words[0].lower() if words else ""


class ReferenceExtractor:
    """Extract references from PDFs."""

    # Patterns for finding references section
    SECTION_PATTERNS = [
        r"(?i)^references?\s*$",
        r"(?i)^bibliography\s*$",
        r"(?i)^works?\s+cited\s*$",
        r"(?i)^literature\s+cited\s*$",
    ]

    # Pattern for DOI - more precise, excludes trailing punctuation
    # Matches DOI format: 10.NNNN/suffix where suffix contains alphanumeric and some punctuation
    DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\])<>,;'\"]+(?<![.,;:)])")

    # Pattern for year in parentheses or standalone
    YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

    # Pattern for page ranges
    PAGES_PATTERN = re.compile(r"\b(\d+)\s*[-–—]\s*(\d+)\b")

    # Pre-compiled patterns for performance
    _COMPILED_SECTION_PATTERNS: list[re.Pattern] | None = None
    _NUMBERED_REF_SPLIT = re.compile(r"\n\s*\[\d+\]\s*")
    _QUOTED_TITLE = re.compile(r'[""\u201c\u201d]([^""\u201c\u201d]+)[""\u201c\u201d]')
    _SINGLE_QUOTED_TITLE = re.compile(r"'([^']+)'")
    _LEADING_PUNCT = re.compile(r"^[.,:\s)]+")
    _SENTENCE_END = re.compile(r"\.\s+[A-Z]")
    _TRAILING_PUNCT = re.compile(r"[.,;:\s]+$")
    _CITATION_PREFIX = re.compile(r"^\s*\[?\d+\]?\.?\s*")
    _TRAILING_AUTHOR_PUNCT = re.compile(r"[\s,.(]+$")
    _CAMEL_CASE = re.compile(r"([a-z])([A-Z])")
    _INITIALS_CONCAT = re.compile(r"\.([A-Z])")
    _DIGITS_ONLY = re.compile(r"^\d+$")
    _INITIALS = re.compile(r"^[A-Z]\.?(?:\s*[A-Z]\.?)*$")
    _FIRST_NAME = re.compile(r"^[A-Z][a-z]{1,10}$")
    # Combined journal patterns for title extraction
    _JOURNAL_PATTERNS = [
        re.compile(r"[,.]?\s*\d+\s*[\(:]"),  # Volume number like "12(" or "12:"
        re.compile(r"[,.]?\s*\d+\s*[-–]\s*\d+"),  # Page range like "100-120"
        re.compile(r"[,.]?\s*[A-Z][a-z]+\s+(?:of|and|for)\s+"),  # "Journal of..."
        re.compile(r"[,.]?\s*(?:Journal|Review|Quarterly|Proceedings|Transactions)\b"),
        re.compile(r"[,.]?\s*In\s+[A-Z]"),  # "In Proceedings..."
        re.compile(r"[,.]?\s*arXiv:"),  # arXiv identifier
        re.compile(r"[,.]?\s*https?://"),  # URL
    ]

    @classmethod
    def _get_compiled_section_patterns(cls) -> list[re.Pattern]:
        """Get pre-compiled section patterns (lazy initialization)."""
        if cls._COMPILED_SECTION_PATTERNS is None:
            cls._COMPILED_SECTION_PATTERNS = [
                re.compile(p) for p in cls.SECTION_PATTERNS
            ]
        return cls._COMPILED_SECTION_PATTERNS

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
        compiled_patterns = self._get_compiled_section_patterns()
        for i, line in enumerate(lines):
            stripped = line.strip()
            for pattern in compiled_patterns:
                if pattern.match(stripped):
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
        numbered = self._NUMBERED_REF_SPLIT.split(refs_text)
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
        # 1. Look for quoted title (double or curly quotes)
        quoted = self._QUOTED_TITLE.search(text)
        if quoted:
            title = quoted.group(1).strip()
            if len(title) > 10:
                return title

        # 2. Look for single-quoted title
        single_quoted = self._SINGLE_QUOTED_TITLE.search(text)
        if single_quoted:
            title = single_quoted.group(1).strip()
            if len(title) > 15:  # Higher threshold for single quotes (avoid contractions)
                return title

        # 3. Try to find title between year and journal/volume indicators
        year_match = self.YEAR_PATTERN.search(text)
        if year_match:
            after_year = text[year_match.end() :].strip()
            # Remove leading punctuation and whitespace
            after_year = self._LEADING_PUNCT.sub("", after_year)

            # Find where title ends (first match of journal pattern or period)
            title_end = len(after_year)
            for pattern in self._JOURNAL_PATTERNS:
                match = pattern.search(after_year)
                if match and match.start() < title_end:
                    title_end = match.start()

            # Also check for sentence-ending period followed by capital letter
            period_match = self._SENTENCE_END.search(after_year)
            if period_match and period_match.start() < title_end:
                title_end = period_match.start()

            if title_end > 0:
                title = after_year[:title_end].strip()
                # Clean trailing punctuation
                title = self._TRAILING_PUNCT.sub("", title)
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
        # Remove citation number prefix like "[1]" or "1."
        author_part = self._CITATION_PREFIX.sub("", author_part)
        # Remove trailing punctuation and parentheses
        author_part = self._TRAILING_AUTHOR_PUNCT.sub("", author_part)

        if not author_part:
            return []

        # Handle "and", "&", semicolons with proper spacing
        # Note: These simple patterns are fast enough inline
        author_part = re.sub(r"\s+and\s+", ", ", author_part, flags=re.IGNORECASE)
        author_part = author_part.replace(" & ", ", ").replace("&", ", ")
        author_part = author_part.replace("; ", ", ").replace(";", ", ")

        # Split by commas
        raw_parts = [a.strip() for a in author_part.split(",") if a.strip()]

        # Reconstruct proper names handling "Last, First" format
        authors = []
        i = 0
        while i < len(raw_parts):
            name = raw_parts[i]

            # Check if this might be "Last, First" format
            # (last name followed by initials or first name on next part)
            if i + 1 < len(raw_parts):
                next_part = raw_parts[i + 1]
                # If next part looks like initials (1-3 chars with optional periods) or first name
                if self._INITIALS.match(next_part) or self._FIRST_NAME.match(next_part):
                    # "Last, First" or "Last, F." or "Last, F. M." format
                    authors.append(f"{next_part} {name}")
                    i += 2
                    continue

            # Fix concatenated names like "JohnSmith" -> "John Smith"
            # Insert space before capital letters that follow lowercase
            spaced_name = self._CAMEL_CASE.sub(r"\1 \2", name)

            # Also handle initials without spaces like "J.Smith" -> "J. Smith"
            spaced_name = self._INITIALS_CONCAT.sub(r". \1", spaced_name)

            authors.append(spaced_name)
            i += 1

        # Clean up authors (remove et al., citation artifacts, etc.)
        cleaned_authors = []
        for a in authors:
            a = a.strip()
            if a.lower() in ("et al", "et al.", "others"):
                continue
            # Skip if it looks like a citation number
            if self._DIGITS_ONLY.match(a):
                continue
            if a:
                cleaned_authors.append(a)

        return cleaned_authors[:10]  # Limit to reasonable number
