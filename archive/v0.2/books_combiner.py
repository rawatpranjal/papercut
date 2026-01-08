"""Combine chapter summaries into cohesive book summaries."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from papercut.books.splitter import Chapter, ChapterSplitter
from papercut.llm.client import LLMClient, get_client
from papercut.llm.prompts import get_template


@dataclass
class ChapterSummary:
    """Summary of a single chapter."""

    chapter: Chapter
    summary: str


@dataclass
class BookSummary:
    """Complete book summary with chapter breakdowns."""

    title: str
    source_path: Path
    chapters: list[ChapterSummary]
    synthesis: str
    total_pages: int

    def to_markdown(self) -> str:
        """Render the book summary as markdown.

        Returns:
            Markdown-formatted book summary.
        """
        parts = [
            f"# {self.title}",
            "",
            f"*{self.total_pages} pages, {len(self.chapters)} chapters*",
            "",
            "---",
            "",
            "## Overview",
            "",
            self.synthesis,
            "",
            "---",
            "",
            "## Chapter Summaries",
            "",
        ]

        for i, cs in enumerate(self.chapters, 1):
            parts.extend([
                f"### {i}. {cs.chapter.title}",
                f"*Pages {cs.chapter.start_page + 1}-{cs.chapter.end_page}*",
                "",
                cs.summary,
                "",
            ])

        return "\n".join(parts)


class BookSummarizer:
    """Orchestrates book summarization across chapters."""

    def __init__(
        self,
        model: Optional[str] = None,
        max_chapter_chars: int = 50000,
    ):
        """Initialize the book summarizer.

        Args:
            model: LLM model to use (default from settings).
            max_chapter_chars: Max characters per chapter for LLM.
        """
        self.client = get_client(model)
        self.splitter = ChapterSplitter()
        self.max_chapter_chars = max_chapter_chars

    def summarize(
        self,
        pdf_path: Path,
        book_title: Optional[str] = None,
        chapters: Optional[list[Chapter]] = None,
    ) -> BookSummary:
        """Generate a complete book summary.

        Args:
            pdf_path: Path to the book PDF.
            book_title: Optional book title (auto-detected if not provided).
            chapters: Optional pre-detected chapters (auto-detected if not provided).

        Returns:
            BookSummary with chapter summaries and synthesis.
        """
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Auto-detect title from first page if not provided
        if not book_title:
            first_page_text = reader.pages[0].extract_text() or ""
            first_lines = first_page_text.split("\n")[:3]
            book_title = " ".join(first_lines).strip()[:100] or pdf_path.stem

        # Detect chapters if not provided
        if chapters is None:
            chapters = self.splitter.detect_chapters(pdf_path)

        # Summarize each chapter
        chapter_summaries = []
        chapter_template = get_template("book_chapter")

        for chapter in chapters:
            chapter_text = self.splitter.get_chapter_text(
                pdf_path, chapter, max_chars=self.max_chapter_chars
            )

            system, user = chapter_template.format(
                chapter_name=chapter.title,
                text=chapter_text,
            )

            summary_text = self.client.complete(
                system_prompt=system,
                user_prompt=user,
            )

            chapter_summaries.append(
                ChapterSummary(chapter=chapter, summary=summary_text)
            )

        # Synthesize chapter summaries
        synthesis = self._synthesize(book_title, chapter_summaries)

        return BookSummary(
            title=book_title,
            source_path=pdf_path,
            chapters=chapter_summaries,
            synthesis=synthesis,
            total_pages=total_pages,
        )

    def _synthesize(
        self,
        book_title: str,
        chapter_summaries: list[ChapterSummary],
    ) -> str:
        """Synthesize chapter summaries into book overview.

        Args:
            book_title: Title of the book.
            chapter_summaries: List of chapter summaries.

        Returns:
            Synthesized book overview.
        """
        # Format chapter summaries for the prompt
        summaries_text = "\n\n---\n\n".join(
            f"### {cs.chapter.title}\n\n{cs.summary}"
            for cs in chapter_summaries
        )

        synthesis_template = get_template("book_synthesis")
        system, user = synthesis_template.format(
            book_title=book_title,
            chapter_summaries=summaries_text,
        )

        return self.client.complete(
            system_prompt=system,
            user_prompt=user,
        )

    def summarize_chapters_only(
        self,
        pdf_path: Path,
        chapters: Optional[list[Chapter]] = None,
    ) -> list[ChapterSummary]:
        """Summarize chapters without synthesis.

        Useful for processing chapters incrementally.

        Args:
            pdf_path: Path to the book PDF.
            chapters: Optional pre-detected chapters.

        Returns:
            List of chapter summaries.
        """
        if chapters is None:
            chapters = self.splitter.detect_chapters(pdf_path)

        chapter_summaries = []
        chapter_template = get_template("book_chapter")

        for chapter in chapters:
            chapter_text = self.splitter.get_chapter_text(
                pdf_path, chapter, max_chars=self.max_chapter_chars
            )

            system, user = chapter_template.format(
                chapter_name=chapter.title,
                text=chapter_text,
            )

            summary_text = self.client.complete(
                system_prompt=system,
                user_prompt=user,
            )

            chapter_summaries.append(
                ChapterSummary(chapter=chapter, summary=summary_text)
            )

        return chapter_summaries
