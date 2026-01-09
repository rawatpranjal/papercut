"""The Sawmill: Chapter detection and PDF splitting for large books.

This module handles splitting large PDFs (500+ pages) into smaller chunks
before they are sent to Docling for processing. This prevents memory issues
and reduces costs for LLM processing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


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


@dataclass
class SplitResult:
    """Result of splitting a PDF."""

    original_path: Path
    chunks: list[tuple[Path, Chapter]]  # (chunk_path, chapter_metadata)
    total_pages: int
    was_split: bool  # True if PDF was split, False if too small

    @property
    def chunk_count(self) -> int:
        """Number of chunks created."""
        return len(self.chunks)


class Splitter:
    """The Sawmill: Detect chapters and split large PDFs.

    This class provides:
    1. Chapter detection using bookmarks or text patterns
    2. PDF splitting for large books (500+ pages)
    3. Chunk extraction for individual chapters
    """

    # Common chapter title patterns
    CHAPTER_PATTERNS = [
        r"^Chapter\s+(\d+|[IVXLC]+)[:\.\s]",  # Chapter 1: / Chapter I.
        r"^CHAPTER\s+(\d+|[IVXLC]+)[:\.\s]",  # CHAPTER 1:
        r"^Part\s+(\d+|[IVXLC]+)[:\.\s]",  # Part 1: / Part I.
        r"^PART\s+(\d+|[IVXLC]+)[:\.\s]",  # PART 1:
        r"^(\d+)\.\s+[A-Z]",  # 1. Title
        r"^Section\s+(\d+)",  # Section 1
        r"^Ch\.?\s*(\d+)",  # Ch 1, Ch. 1
        r"^Unit\s+(\d+)",  # Unit 1
        r"^UNIT\s+(\d+)",  # UNIT 1
        r"^Module\s+(\d+)",  # Module 1
        r"^MODULE\s+(\d+)",  # MODULE 1
        r"^Lecture\s+(\d+)",  # Lecture 1
        r"^LECTURE\s+(\d+)",  # LECTURE 1
        r"^Appendix\s+[A-Z]",  # Appendix A
        r"^APPENDIX\s+[A-Z]",  # APPENDIX A
        r"^Lesson\s+(\d+)",  # Lesson 1
        r"^LESSON\s+(\d+)",  # LESSON 1
    ]

    # Pre-compiled patterns for performance
    _COMPILED_CHAPTER_PATTERNS: list[re.Pattern] | None = None

    @classmethod
    def _get_compiled_patterns(cls) -> list[re.Pattern]:
        """Get pre-compiled chapter patterns (lazy initialization)."""
        if cls._COMPILED_CHAPTER_PATTERNS is None:
            cls._COMPILED_CHAPTER_PATTERNS = [
                re.compile(p, re.MULTILINE) for p in cls.CHAPTER_PATTERNS
            ]
        return cls._COMPILED_CHAPTER_PATTERNS

    def __init__(
        self,
        min_chapter_pages: int = 3,
        split_threshold_pages: int = 500,
        max_chunk_pages: int = 100,
    ):
        """Initialize the splitter.

        Args:
            min_chapter_pages: Minimum pages for a valid chapter.
            split_threshold_pages: Split books larger than this.
            max_chunk_pages: Maximum pages per chunk when no chapters found.
        """
        self.min_chapter_pages = min_chapter_pages
        self.split_threshold_pages = split_threshold_pages
        self.max_chunk_pages = max_chunk_pages

    def should_split(self, pdf_path: Path) -> bool:
        """Check if a PDF should be split based on page count.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            True if PDF exceeds the split threshold.
        """
        reader = PdfReader(pdf_path)
        return len(reader.pages) >= self.split_threshold_pages

    def get_page_count(self, pdf_path: Path) -> int:
        """Get the page count of a PDF.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Number of pages.
        """
        reader = PdfReader(pdf_path)
        return len(reader.pages)

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

    def split_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        prefix: str = "chunk",
    ) -> SplitResult:
        """Split a large PDF into smaller chunks.

        Uses chapters if detected, otherwise splits by page count.

        Args:
            pdf_path: Path to the PDF file.
            output_dir: Directory to save chunks.
            prefix: Prefix for chunk filenames.

        Returns:
            SplitResult with paths to created chunks.
        """
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Check if we need to split at all
        if total_pages < self.split_threshold_pages:
            return SplitResult(
                original_path=pdf_path,
                chunks=[(pdf_path, Chapter("Full Document", 0, total_pages))],
                total_pages=total_pages,
                was_split=False,
            )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Detect chapters
        chapters = self.detect_chapters(pdf_path)

        # If only one chapter (full book), split by page count
        if len(chapters) == 1 and chapters[0].title == "Full Book":
            chapters = self._split_by_pages(total_pages)

        # Create chunk PDFs
        chunks: list[tuple[Path, Chapter]] = []
        for i, chapter in enumerate(chapters):
            chunk_path = output_dir / f"{prefix}_{i + 1:03d}.pdf"
            self._write_chunk(reader, chapter, chunk_path)
            chunks.append((chunk_path, chapter))
            logger.debug(f"Created chunk: {chunk_path} ({chapter.page_count} pages)")

        return SplitResult(
            original_path=pdf_path,
            chunks=chunks,
            total_pages=total_pages,
            was_split=True,
        )

    def extract_chapter(
        self,
        pdf_path: Path,
        chapter: Chapter,
        output_path: Path,
    ) -> Path:
        """Extract a single chapter to a new PDF.

        Args:
            pdf_path: Path to the source PDF.
            chapter: Chapter to extract.
            output_path: Path for the output PDF.

        Returns:
            Path to the created PDF.
        """
        reader = PdfReader(pdf_path)
        self._write_chunk(reader, chapter, output_path)
        return output_path

    def _write_chunk(
        self,
        reader: PdfReader,
        chapter: Chapter,
        output_path: Path,
    ) -> None:
        """Write a chunk of pages to a new PDF.

        Args:
            reader: Source PDF reader.
            chapter: Chapter defining page range.
            output_path: Path for the output PDF.
        """
        writer = PdfWriter()

        for page_num in range(chapter.start_page, chapter.end_page):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

    def _split_by_pages(self, total_pages: int) -> list[Chapter]:
        """Create chapters by splitting at fixed page intervals.

        Args:
            total_pages: Total pages in the document.

        Returns:
            List of chapters based on page ranges.
        """
        chapters = []
        start = 0
        chunk_num = 1

        while start < total_pages:
            end = min(start + self.max_chunk_pages, total_pages)
            chapters.append(
                Chapter(
                    title=f"Chunk {chunk_num} (Pages {start + 1}-{end})",
                    start_page=start,
                    end_page=end,
                )
            )
            start = end
            chunk_num += 1

        return chapters

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

        chapters: list[Chapter] = []
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
                            # Skip if page number couldn't be determined
                            if page_num is None:
                                continue
                            chapters.append(
                                Chapter(
                                    title=title.strip(),
                                    start_page=page_num,
                                    end_page=page_num + 1,  # Will be updated later
                                    level=level,
                                )
                            )
                except Exception as e:
                    # Log and skip malformed outline entries
                    logger.debug(f"Skipping malformed bookmark entry: {e}")
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
        compiled_patterns = self._get_compiled_patterns()

        for page_num in range(total_pages):
            page = reader.pages[page_num]
            text = page.extract_text() or ""

            # Check first 15 lines for chapter headers
            first_lines = "\n".join(text.split("\n")[:15])

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
