"""Paper summarization using LLM."""

from dataclasses import dataclass
from pathlib import Path

from papercutter.extractors.pdfplumber import PdfPlumberExtractor
from papercutter.legacy.core.text import TextExtractor
from papercutter.llm import get_client
from papercutter.llm.prompts import get_summarize_prompt


@dataclass
class Summary:
    """Generated summary of a paper."""

    content: str
    focus: str | None
    length: str
    model: str
    input_tokens: int
    output_tokens: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "summary": self.content,
            "focus": self.focus,
            "length": self.length,
            "model": self.model,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
            },
        }


class Summarizer:
    """Generate summaries of academic papers using LLM."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        extractor: TextExtractor | None = None,
    ):
        """Initialize the summarizer.

        Args:
            api_key: Optional API key.
            model: Optional model to use.
            extractor: Optional TextExtractor instance (for dependency injection).
                      Creates a default PdfPlumberExtractor-based extractor if not provided.
        """
        self.client = get_client(api_key=api_key, model=model)
        self.extractor = extractor or TextExtractor(PdfPlumberExtractor())

    def summarize(
        self,
        pdf_path: Path,
        focus: str | None = None,
        length: str = "default",
        pages: list[int] | None = None,
    ) -> Summary:
        """Generate a summary of a paper.

        Args:
            pdf_path: Path to PDF file.
            focus: Optional focus area (methods, results, etc.).
            length: Summary length (short, default, long).
            pages: Optional list of pages to summarize (0-indexed).

        Returns:
            Summary object.
        """
        # Extract text
        text = self.extractor.extract(pdf_path, pages=pages)

        # Truncate if too long (LLM context limits)
        max_chars = 100000  # ~25k tokens
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated due to length]"

        # Get prompts
        system_prompt, user_prompt = get_summarize_prompt(
            content=text,
            focus=focus,
            length=length,
        )

        # Generate summary
        response = self.client.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=2048 if length == "long" else 1024,
        )

        return Summary(
            content=response.content,
            focus=focus,
            length=length,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    def is_available(self) -> bool:
        """Check if summarization is available."""
        return self.client.is_available()
