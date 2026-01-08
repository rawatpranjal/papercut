"""Report generation logic."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from papercut.core.text import TextExtractor
from papercut.exceptions import ExtractionError, PapercutError
from papercut.extractors.pdfplumber import PdfPlumberExtractor
from papercut.llm.client import LLMClient, check_llm_available
from papercut.llm.prompts import TEMPLATES, PromptTemplate, get_template


@dataclass
class Report:
    """Generated report from a paper."""

    content: str
    template: str
    format: str
    source_path: Path
    metadata: dict[str, Any]

    def save(self, path: Path) -> None:
        """Save report to file.

        Args:
            path: Output file path.
        """
        path.write_text(self.content)


class ReportGenerator:
    """Generate reports from academic papers using LLM."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Initialize report generator.

        Args:
            model: LLM model to use.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
        """
        if not check_llm_available():
            raise PapercutError(
                "LLM features require litellm",
                details="Install with: pip install papercut[llm]",
            )

        self.client = LLMClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.extractor = TextExtractor(PdfPlumberExtractor())

    def generate(
        self,
        pdf_path: Path,
        template: str = "reading_group",
        output_format: str = "markdown",
        **kwargs: Any,
    ) -> Report:
        """Generate a report from a PDF.

        Args:
            pdf_path: Path to PDF file.
            template: Template name (reading_group, meta_analysis, etc.).
            output_format: Output format (markdown, json, latex).
            **kwargs: Additional template variables.

        Returns:
            Generated Report object.

        Raises:
            ExtractionError: If PDF extraction fails.
            PapercutError: If template not found or LLM fails.
        """
        pdf_path = Path(pdf_path)

        # Get template
        prompt_template = get_template(template)
        if not prompt_template:
            available = ", ".join(TEMPLATES.keys())
            raise PapercutError(
                f"Unknown template: {template}",
                details=f"Available templates: {available}",
            )

        # Extract text from PDF
        text = self.extractor.extract(pdf_path)
        if not text:
            raise ExtractionError(
                f"No text extracted from {pdf_path.name}",
            )

        # Truncate if too long (leave room for response)
        max_input_chars = 100000  # ~25k tokens
        if len(text) > max_input_chars:
            text = text[:max_input_chars] + "\n\n[... text truncated ...]"

        # Format prompt
        template_vars = {"text": text, **kwargs}
        system_prompt, user_prompt = prompt_template.format(**template_vars)

        # Generate report
        if output_format == "json" or template == "meta_analysis":
            content = self.client.complete_structured(
                prompt=user_prompt,
                system=system_prompt,
            )
        else:
            content = self.client.complete(
                prompt=user_prompt,
                system=system_prompt,
            )

        # Post-process based on format
        if output_format == "latex":
            content = self._to_latex(content)

        return Report(
            content=content,
            template=template,
            format=output_format,
            source_path=pdf_path,
            metadata={
                "model": self.client.model,
                "template": template,
            },
        )

    def _to_latex(self, markdown_content: str) -> str:
        """Convert markdown to LaTeX snippet.

        Args:
            markdown_content: Markdown text.

        Returns:
            LaTeX formatted text.
        """
        content = markdown_content

        # Convert markdown headers to LaTeX
        import re

        content = re.sub(r"^## (.+)$", r"\\subsection{\1}", content, flags=re.MULTILINE)
        content = re.sub(r"^# (.+)$", r"\\section{\1}", content, flags=re.MULTILINE)

        # Convert bold and italic
        content = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", content)
        content = re.sub(r"\*(.+?)\*", r"\\textit{\1}", content)

        # Convert bullet points
        lines = content.split("\n")
        in_list = False
        result = []

        for line in lines:
            if line.strip().startswith("- "):
                if not in_list:
                    result.append("\\begin{itemize}")
                    in_list = True
                result.append("  \\item " + line.strip()[2:])
            else:
                if in_list:
                    result.append("\\end{itemize}")
                    in_list = False
                result.append(line)

        if in_list:
            result.append("\\end{itemize}")

        return "\n".join(result)


def generate_report(
    pdf_path: Path,
    template: str = "reading_group",
    output_format: str = "markdown",
    model: Optional[str] = None,
    **kwargs: Any,
) -> Report:
    """Convenience function to generate a report.

    Args:
        pdf_path: Path to PDF file.
        template: Template name.
        output_format: Output format.
        model: LLM model to use.
        **kwargs: Additional template variables.

    Returns:
        Generated Report object.
    """
    generator = ReportGenerator(model=model)
    return generator.generate(
        pdf_path=pdf_path,
        template=template,
        output_format=output_format,
        **kwargs,
    )
