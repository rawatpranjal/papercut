"""Report generation using LLM."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from papercut.core.text import TextExtractor
from papercut.extractors.pdfplumber import PdfPlumberExtractor
from papercut.llm import get_client
from papercut.llm.prompts import get_report_prompt


BUILTIN_TEMPLATES = ["reading-group", "referee", "meta", "executive"]


@dataclass
class Report:
    """Generated report about a paper."""

    content: str
    template: str
    model: str
    input_tokens: int
    output_tokens: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "report": self.content,
            "template": self.template,
            "model": self.model,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
            },
        }


class ReportGenerator:
    """Generate structured reports about papers using LLM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize the report generator.

        Args:
            api_key: Optional API key.
            model: Optional model to use.
        """
        self.client = get_client(api_key=api_key, model=model)
        self.extractor = TextExtractor(PdfPlumberExtractor())

    def generate(
        self,
        pdf_path: Path,
        template: str = "reading-group",
        custom_template: Optional[Path] = None,
        pages: Optional[list[int]] = None,
    ) -> Report:
        """Generate a report for a paper.

        Args:
            pdf_path: Path to PDF file.
            template: Template name (reading-group, referee, meta, executive).
            custom_template: Path to custom template file.
            pages: Optional list of pages to analyze (0-indexed).

        Returns:
            Report object.
        """
        # Extract text
        text = self.extractor.extract(pdf_path, pages=pages)

        # Truncate if too long
        max_chars = 100000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated due to length]"

        # Handle custom template
        if custom_template:
            template_content = custom_template.read_text()
            system_prompt = "You are a research assistant. Follow the template exactly."
            user_prompt = template_content.replace("{content}", text)
            template_name = custom_template.name
        else:
            system_prompt, user_prompt = get_report_prompt(
                content=text,
                template=template,
            )
            template_name = template

        # Generate report
        response = self.client.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=4096,
        )

        return Report(
            content=response.content,
            template=template_name,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    def list_templates(self) -> list[str]:
        """List available built-in templates."""
        return BUILTIN_TEMPLATES.copy()

    def is_available(self) -> bool:
        """Check if report generation is available."""
        return self.client.is_available()
