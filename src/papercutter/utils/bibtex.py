"""BibTeX generation utilities for Papercutter Factory.

Provides utilities for generating BibTeX entries and citation keys.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BibTeXEntry:
    """Represents a BibTeX entry.

    Handles generation of properly formatted BibTeX with sanitized values.
    """

    entry_type: str = "misc"  # article, inproceedings, book, misc, etc.
    key: str = ""  # Citation key (e.g., vaswani2017attention)

    # Core fields
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None

    # Journal/book fields
    journal: str | None = None
    booktitle: str | None = None  # For inproceedings
    publisher: str | None = None
    volume: str | None = None
    number: str | None = None
    pages: str | None = None

    # Identifiers
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None

    # Additional
    abstract: str | None = None
    keywords: list[str] = field(default_factory=list)

    def to_bibtex(self, used_keys: set[str] | None = None) -> str:
        """Convert to BibTeX format string.

        Args:
            used_keys: Optional set of already-used citation keys. If provided,
                      ensures uniqueness by appending suffixes. The set is modified
                      in-place to include the new key.

        Returns:
            BibTeX entry string.
        """
        # Generate unique key if needed
        key = self._generate_unique_key(used_keys)

        lines = [f"@{self.entry_type}{{{key},"]

        if self.authors:
            sanitized_authors = [self._sanitize_value(a) for a in self.authors]
            author_str = " and ".join(sanitized_authors)
            lines.append(f"  author = {{{author_str}}},")

        if self.title:
            lines.append(f"  title = {{{self._sanitize_value(self.title)}}},")

        if self.year:
            lines.append(f"  year = {{{self.year}}},")

        if self.journal:
            lines.append(f"  journal = {{{self._sanitize_value(self.journal)}}},")

        if self.booktitle:
            lines.append(f"  booktitle = {{{self._sanitize_value(self.booktitle)}}},")

        if self.publisher:
            lines.append(f"  publisher = {{{self._sanitize_value(self.publisher)}}},")

        if self.volume:
            lines.append(f"  volume = {{{self.volume}}},")

        if self.number:
            lines.append(f"  number = {{{self.number}}},")

        if self.pages:
            lines.append(f"  pages = {{{self.pages}}},")

        if self.doi:
            lines.append(f"  doi = {{{self.doi}}},")

        if self.arxiv_id:
            lines.append(f"  eprint = {{{self.arxiv_id}}},")
            lines.append("  archiveprefix = {arXiv},")

        if self.url:
            lines.append(f"  url = {{{self.url}}},")

        if self.abstract:
            lines.append(f"  abstract = {{{self._sanitize_value(self.abstract)}}},")

        if self.keywords:
            lines.append(f"  keywords = {{{', '.join(self.keywords)}}},")

        lines.append("}")
        return "\n".join(lines)

    def _sanitize_value(self, value: str) -> str:
        """Sanitize a value for BibTeX output.

        Removes newlines, normalizes whitespace, and escapes special characters.

        Args:
            value: The value to sanitize.

        Returns:
            Sanitized value safe for BibTeX.
        """
        if not value:
            return value
        # Replace newlines and multiple spaces with single space
        sanitized = re.sub(r"\s+", " ", value)
        # Escape special BibTeX characters (# $ % & _ { } ~ ^)
        for char in ["#", "$", "%", "&", "_", "{", "}", "~", "^"]:
            sanitized = sanitized.replace(char, "\\" + char)
        return sanitized.strip()

    def _generate_key(self) -> str:
        """Generate a BibTeX citation key.

        Returns:
            Citation key string (e.g., 'vaswani2017attention').
        """
        if self.key:
            return self.key

        author_part = self._extract_last_name(self.authors[0]) if self.authors else "unknown"
        year_part = str(self.year) if self.year else "0000"
        title_part = self._extract_title_word(self.title) if self.title else ""

        return f"{author_part}{year_part}{title_part}"

    def _generate_unique_key(self, used_keys: set[str] | None = None) -> str:
        """Generate a unique BibTeX citation key.

        Args:
            used_keys: Set of already-used keys. Modified in-place if provided.

        Returns:
            Unique citation key string.
        """
        base_key = self._generate_key()

        if used_keys is None:
            return base_key

        key = base_key
        counter = 2
        while key in used_keys:
            key = f"{base_key}_{counter}"
            counter += 1

        used_keys.add(key)
        return key

    def _extract_last_name(self, author: str) -> str:
        """Extract last name from author string.

        Handles formats like:
        - "Smith, John" -> "smith"
        - "John Smith" -> "smith"
        - "van der Berg, Jan" -> "vandenberg"

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
                        last_name_parts = parts[i:]
                        break
                if not last_name_parts:
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
            word_lower: str = word.lower()
            if word_lower not in skip_words and len(word_lower) > 1:
                return word_lower

        return str(words[0].lower()) if words else ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entry_type": self.entry_type,
            "key": self.key or self._generate_key(),
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "booktitle": self.booktitle,
            "publisher": self.publisher,
            "volume": self.volume,
            "number": self.number,
            "pages": self.pages,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BibTeXEntry:
        """Create from dictionary."""
        return cls(
            entry_type=data.get("entry_type", "misc"),
            key=data.get("key", ""),
            title=data.get("title"),
            authors=data.get("authors", []),
            year=data.get("year"),
            journal=data.get("journal"),
            booktitle=data.get("booktitle"),
            publisher=data.get("publisher"),
            volume=data.get("volume"),
            number=data.get("number"),
            pages=data.get("pages"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            url=data.get("url"),
            abstract=data.get("abstract"),
            keywords=data.get("keywords", []),
        )


def generate_citation_key(
    authors: list[str],
    year: int | None,
    title: str | None,
    used_keys: set[str] | None = None,
) -> str:
    """Generate a citation key from metadata.

    Args:
        authors: List of author names.
        year: Publication year.
        title: Paper title.
        used_keys: Optional set of already-used keys for uniqueness.

    Returns:
        Citation key string.
    """
    entry = BibTeXEntry(authors=authors, year=year, title=title)
    return entry._generate_unique_key(used_keys)


def format_authors_bibtex(authors: list[str]) -> str:
    """Format author list for BibTeX (joined with ' and ').

    Args:
        authors: List of author names.

    Returns:
        BibTeX-formatted author string.
    """
    return " and ".join(authors)
