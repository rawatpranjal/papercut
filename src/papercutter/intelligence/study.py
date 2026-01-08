"""Study aid generation using LLM."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from papercutter.core.text import TextExtractor
from papercutter.extractors.pdfplumber import PdfPlumberExtractor
from papercutter.llm import get_client
from papercutter.llm.prompts import get_study_prompt


STUDY_MODES = ["summary", "concepts", "quiz", "flashcards"]


@dataclass
class StudyMaterial:
    """Generated study material."""

    content: str
    mode: str
    chapter: Optional[int]
    model: str
    input_tokens: int
    output_tokens: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "material": self.content,
            "mode": self.mode,
            "chapter": self.chapter,
            "model": self.model,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
            },
        }


class StudyAid:
    """Generate study materials from book chapters using LLM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        extractor: Optional[TextExtractor] = None,
    ):
        """Initialize the study aid.

        Args:
            api_key: Optional API key.
            model: Optional model to use.
            extractor: Optional TextExtractor instance (for dependency injection).
                      Creates a default PdfPlumberExtractor-based extractor if not provided.
        """
        self.client = get_client(api_key=api_key, model=model)
        self.extractor = extractor or TextExtractor(PdfPlumberExtractor())

    def generate(
        self,
        pdf_path: Path,
        mode: str = "summary",
        chapter: Optional[int] = None,
        pages: Optional[list[int]] = None,
    ) -> StudyMaterial:
        """Generate study material.

        Args:
            pdf_path: Path to PDF file.
            mode: Study mode (summary, concepts, quiz, flashcards).
            chapter: Optional chapter ID to extract.
            pages: Optional list of pages (0-indexed). Used if chapter not provided.

        Returns:
            StudyMaterial object.
        """
        # If chapter specified, get pages from index
        if chapter is not None:
            from papercutter.index import DocumentIndexer

            indexer = DocumentIndexer()
            doc_index = indexer.index(pdf_path, doc_type="book")

            # Find chapter
            found_chapter = None
            for ch in doc_index.chapters:
                if ch["id"] == chapter:
                    found_chapter = ch
                    break

            if not found_chapter:
                raise ValueError(f"Chapter {chapter} not found")

            pages = list(range(found_chapter["pages"][0] - 1, found_chapter["pages"][1]))

        # Extract text
        text = self.extractor.extract(pdf_path, pages=pages)

        # Truncate if too long
        max_chars = 80000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated due to length]"

        # Get prompts
        system_prompt, user_prompt = get_study_prompt(
            content=text,
            mode=mode,
        )

        # Determine max tokens based on mode
        max_tokens = {
            "summary": 2048,
            "concepts": 3000,
            "quiz": 3000,
            "flashcards": 4000,
        }.get(mode, 2048)

        # Generate material
        response = self.client.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=max_tokens,
        )

        return StudyMaterial(
            content=response.content,
            mode=mode,
            chapter=chapter,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    def list_modes(self) -> list[str]:
        """List available study modes."""
        return STUDY_MODES.copy()

    def is_available(self) -> bool:
        """Check if study aid is available."""
        return self.client.is_available()
