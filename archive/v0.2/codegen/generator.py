"""Generate simulation code from academic papers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from papercut.core.text import TextExtractor
from papercut.extractors.pdfplumber import PdfPlumberExtractor
from papercut.llm.client import get_client
from papercut.llm.prompts import get_template


Language = Literal["python", "r"]


@dataclass
class GeneratedCode:
    """Generated simulation code from a paper."""

    language: Language
    code: str
    source_path: Path
    model_description: Optional[str] = None

    @property
    def file_extension(self) -> str:
        """Get the appropriate file extension."""
        return ".py" if self.language == "python" else ".R"

    def save(self, output_path: Path) -> Path:
        """Save the code to a file.

        Args:
            output_path: Output file path.

        Returns:
            Path to saved file.
        """
        output_path.write_text(self.code)
        return output_path

    def default_filename(self) -> str:
        """Generate a default filename based on source."""
        stem = self.source_path.stem.replace(" ", "_").lower()
        return f"{stem}_simulation{self.file_extension}"


class SimulationGenerator:
    """Generate simulation code from academic papers."""

    def __init__(
        self,
        model: Optional[str] = None,
        max_text_chars: int = 60000,
    ):
        """Initialize the simulation generator.

        Args:
            model: LLM model to use.
            max_text_chars: Maximum text characters to send to LLM.
        """
        self.client = get_client(model)
        self.max_text_chars = max_text_chars
        self.text_extractor = TextExtractor(PdfPlumberExtractor())

    def generate(
        self,
        pdf_path: Path,
        language: Language = "python",
    ) -> GeneratedCode:
        """Generate simulation code from a paper.

        Args:
            pdf_path: Path to the PDF paper.
            language: Target programming language.

        Returns:
            GeneratedCode with the simulation implementation.
        """
        # Extract text
        text = self.text_extractor.extract(pdf_path)
        if len(text) > self.max_text_chars:
            text = text[: self.max_text_chars] + "\n\n[Text truncated...]"

        # Get simulation template
        template = get_template("simulation")
        system, user = template.format(
            language=language.capitalize(),
            text=text,
        )

        # Generate code
        response = self.client.complete(
            system_prompt=system,
            user_prompt=user,
        )

        # Extract code from response
        code = self._extract_code(response, language)

        return GeneratedCode(
            language=language,
            code=code,
            source_path=pdf_path,
        )

    def generate_both(self, pdf_path: Path) -> tuple[GeneratedCode, GeneratedCode]:
        """Generate both Python and R versions.

        Args:
            pdf_path: Path to the PDF paper.

        Returns:
            Tuple of (python_code, r_code).
        """
        python_code = self.generate(pdf_path, language="python")
        r_code = self.generate(pdf_path, language="r")
        return python_code, r_code

    def _extract_code(self, response: str, language: Language) -> str:
        """Extract code from LLM response.

        Handles markdown code blocks and plain code.

        Args:
            response: Raw LLM response.
            language: Expected language.

        Returns:
            Cleaned code string.
        """
        text = response.strip()

        # Check for markdown code blocks
        lang_markers = {
            "python": ["```python", "```py"],
            "r": ["```r", "```R"],
        }

        markers = lang_markers.get(language, [])
        markers.append("```")  # Generic code block

        for marker in markers:
            if marker in text:
                # Find the code block
                start = text.find(marker)
                if start >= 0:
                    start = text.find("\n", start) + 1
                    end = text.find("```", start)
                    if end > start:
                        return text[start:end].strip()

        # No code block found, return as-is
        # but try to remove any non-code preamble
        lines = text.split("\n")
        code_lines = []
        in_code = False

        for line in lines:
            # Detect start of code
            if not in_code:
                if language == "python" and (
                    line.startswith("import ")
                    or line.startswith("from ")
                    or line.startswith("def ")
                    or line.startswith("class ")
                    or line.startswith("#")
                    or line.startswith('"""')
                ):
                    in_code = True
                elif language == "r" and (
                    line.startswith("library(")
                    or line.startswith("#")
                    or "<-" in line
                    or "function(" in line
                ):
                    in_code = True

            if in_code:
                code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines)

        # Fallback: return everything
        return text
