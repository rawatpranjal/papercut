"""Chapter detection and splitting for book PDFs."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pypdf import PdfReader


@dataclass
class Chapter:
    """A detected chapter in a book."""

    title: str
    start_page: int  # 0-indexed
    end_page: int  # 0-indexed, exclusive
    level: int = 1  # Hierarchy level (1=chapter, 2=section, etc.)

    @property
    def page_count(self) -> int:
        """Number of pages in this chapter."""
        return self.end_page - self.start_page

    def __repr__(self) -> str:
        return f"Chapter('{self.title}', pages {self.start_page + 1}-{self.end_page})"


class ChapterSplitter:
    """Detect and split chapters from book PDFs."""

    # Common chapter title patterns
    CHAPTER_PATTERNS = [
        r"^Chapter\s+(\d+|[IVXLC]+)[:\.\s]",  # Chapter 1: / Chapter I.
        r"^CHAPTER\s+(\d+|[IVXLC]+)[:\.\s]",  # CHAPTER 1:
        r"^Part\s+(\d+|[IVXLC]+)[:\.\s]",  # Part 1: / Part I.
        r"^PART\s+(\d+|[IVXLC]+)[:\.\s]",  # PART 1:
        r"^(\d+)\.\s+[A-Z]",  # 1. Title
        r"^Section\s+(\d+)",  # Section 1
    ]

    def __init__(self, min_chapter_pages: int = 3):
        """Initialize the chapter splitter.

        Args:
            min_chapter_pages: Minimum pages for a valid chapter.
        """
        self.min_chapter_pages = min_chapter_pages

    def detect_chapters(self, pdf_path: Path) -> list[Chapter]:
        """Detect chapters in a PDF using bookmarks and text patterns.

        Tries bookmark/outline first, falls back to text pattern matching.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of detected chapters.
        """
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Try bookmarks first
        chapters = self._from_bookmarks(reader, total_pages)
        if chapters:
            return chapters

        # Fall back to text pattern detection
        chapters = self._from_text_patterns(reader, total_pages)
        if chapters:
            return chapters

        # Last resort: treat entire book as one chapter
        return [Chapter(title="Full Book", start_page=0, end_page=total_pages)]

    def _from_bookmarks(self, reader: PdfReader, total_pages: int) -> list[Chapter]:
        """Extract chapters from PDF bookmarks/outline.

        Args:
            reader: PdfReader instance.
            total_pages: Total number of pages.

        Returns:
            List of chapters from bookmarks, or empty list if none.
        """
        outline = reader.outline
        if not outline:
            return []

        chapters = []
        self._extract_outline_items(reader, outline, chapters, level=1)

        if not chapters:
            return []

        # Sort by start page
        chapters.sort(key=lambda c: c.start_page)

        # Set end pages based on next chapter start
        for i, chapter in enumerate(chapters):
            if i + 1 < len(chapters):
                chapter.end_page = chapters[i + 1].start_page
            else:
                chapter.end_page = total_pages

        # Filter out tiny chapters
        chapters = [c for c in chapters if c.page_count >= self.min_chapter_pages]

        return chapters

    def _extract_outline_items(
        self,
        reader: PdfReader,
        outline: list,
        chapters: list[Chapter],
        level: int,
    ) -> None:
        """Recursively extract outline items.

        Args:
            reader: PdfReader instance.
            outline: Outline items to process.
            chapters: List to append chapters to.
            level: Current hierarchy level.
        """
        for item in outline:
            if isinstance(item, list):
                # Nested outline - recurse
                self._extract_outline_items(reader, item, chapters, level + 1)
            else:
                # Destination item
                try:
                    title = item.title if hasattr(item, "title") else str(item)
                    # Get page number from destination
                    if hasattr(item, "page"):
                        page_obj = item.page
                        if page_obj is not None:
                            page_num = reader.get_page_number(page_obj)
                            chapters.append(
                                Chapter(
                                    title=title.strip(),
                                    start_page=page_num,
                                    end_page=page_num + 1,  # Will be updated later
                                    level=level,
                                )
                            )
                except Exception:
                    # Skip malformed outline entries
                    continue

    def _from_text_patterns(
        self, reader: PdfReader, total_pages: int
    ) -> list[Chapter]:
        """Detect chapters using text pattern matching.

        Args:
            reader: PdfReader instance.
            total_pages: Total number of pages.

        Returns:
            List of detected chapters.
        """
        chapters = []
        compiled_patterns = [re.compile(p, re.MULTILINE) for p in self.CHAPTER_PATTERNS]

        for page_num in range(total_pages):
            page = reader.pages[page_num]
            text = page.extract_text() or ""

            # Check first few lines for chapter headers
            first_lines = "\n".join(text.split("\n")[:5])

            for pattern in compiled_patterns:
                match = pattern.search(first_lines)
                if match:
                    # Extract chapter title (rest of the line)
                    line_start = text.find(match.group())
                    line_end = text.find("\n", line_start)
                    if line_end == -1:
                        line_end = len(text)
                    title = text[line_start:line_end].strip()

                    # Truncate very long titles
                    if len(title) > 100:
                        title = title[:100] + "..."

                    chapters.append(
                        Chapter(
                            title=title,
                            start_page=page_num,
                            end_page=page_num + 1,  # Will be updated
                        )
                    )
                    break  # Found a match, move to next page

        if not chapters:
            return []

        # Set end pages
        for i, chapter in enumerate(chapters):
            if i + 1 < len(chapters):
                chapter.end_page = chapters[i + 1].start_page
            else:
                chapter.end_page = total_pages

        # Filter tiny chapters
        chapters = [c for c in chapters if c.page_count >= self.min_chapter_pages]

        return chapters

    def get_chapter_text(
        self,
        pdf_path: Path,
        chapter: Chapter,
        max_chars: Optional[int] = None,
    ) -> str:
        """Extract text for a specific chapter.

        Args:
            pdf_path: Path to the PDF file.
            chapter: Chapter to extract.
            max_chars: Maximum characters to extract (for LLM context limits).

        Returns:
            Extracted chapter text.
        """
        from papercut.core.text import TextExtractor
        from papercut.extractors.pdfplumber import PdfPlumberExtractor

        extractor = TextExtractor(PdfPlumberExtractor())
        pages = list(range(chapter.start_page, chapter.end_page))

        text = extractor.extract(pdf_path, pages=pages)

        if max_chars and len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated due to length...]"

        return text
