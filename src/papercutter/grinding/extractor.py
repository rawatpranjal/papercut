"""Evidence extractor for Papercutter Factory.

Uses LLM to extract structured evidence from papers based on a schema.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from papercutter.exceptions import LLMNotAvailableError
from papercutter.grinding.matrix import (
    ExtractedValue,
    ExtractionMatrix,
    PaperExtraction,
)
from papercutter.grinding.schema import ExtractionSchema, FieldType
from papercutter.llm.client import LLMClient, get_client

logger = logging.getLogger(__name__)

# Maximum content to send to LLM per paper
MAX_CONTENT_CHARS = 100000

EXTRACTION_SYSTEM = """You are an expert research assistant extracting structured evidence from academic papers.

Your task is to carefully read the paper and extract specific information according to the provided schema.

Guidelines:
1. Extract information exactly as requested in the schema
2. Use direct quotes when possible, noting page numbers if available
3. For numerical data, include units and confidence intervals if given
4. If information is not found, return "N/A"
5. For categorical fields, use only the provided options
6. Be precise and factual - do not infer or speculate"""

EXTRACTION_PROMPT = """Extract the following information from this paper:

{schema_prompt}

Paper content:
{content}

Return your extractions as a JSON object with this structure:
{{
  "field_key": {{
    "value": "extracted value",
    "quote": "direct quote from paper (optional)",
    "page": page_number_if_known
  }},
  ...
}}

For fields where information is not found, use:
{{"value": "N/A"}}

Return ONLY the JSON object, no other text."""


@dataclass
class ExtractionProgress:
    """Progress update during extraction."""

    current: int
    total: int
    paper_id: str
    status: str  # "extracting", "completed", "failed"


@dataclass
class ExtractorResult:
    """Result of extraction run."""

    papers_processed: int = 0
    papers_succeeded: int = 0
    papers_failed: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)
    """List of (paper_id, error_message)."""


class Extractor:
    """Extracts structured evidence from papers using LLM.

    Uses the extraction schema to build prompts and parse responses
    into structured data for the extraction matrix.
    """

    def __init__(
        self,
        schema: ExtractionSchema,
        llm_client: LLMClient | None = None,
        max_content_chars: int = MAX_CONTENT_CHARS,
    ):
        """Initialize the extractor.

        Args:
            schema: Extraction schema defining what to extract.
            llm_client: LLM client to use.
            max_content_chars: Maximum content per paper to send to LLM.
        """
        self.schema = schema
        self.llm_client = llm_client
        self.max_content_chars = max_content_chars

    def _get_client(self) -> LLMClient:
        """Get or create LLM client."""
        if self.llm_client is None:
            self.llm_client = get_client()
        return self.llm_client

    def extract(
        self,
        paper_id: str,
        content: str,
        title: str | None = None,
        bibtex_key: str | None = None,
    ) -> PaperExtraction:
        """Extract evidence from a single paper.

        Args:
            paper_id: Unique identifier for the paper.
            content: Paper content (markdown).
            title: Optional paper title.
            bibtex_key: Optional BibTeX key.

        Returns:
            PaperExtraction with extracted values.
        """
        extraction = PaperExtraction(
            paper_id=paper_id,
            title=title,
            bibtex_key=bibtex_key,
        )

        # Truncate content if needed
        if len(content) > self.max_content_chars:
            content = content[: self.max_content_chars] + "\n\n[Content truncated...]"

        # Build schema prompt
        schema_prompt = self.schema.to_extraction_prompt()

        # Build full prompt
        prompt = EXTRACTION_PROMPT.format(
            schema_prompt=schema_prompt,
            content=content,
        )

        # Call LLM
        client = self._get_client()
        try:
            response = client.complete(
                prompt=prompt,
                system=EXTRACTION_SYSTEM,
                max_tokens=2000,
                temperature=0.1,  # Low temperature for factual extraction
            )

            # Parse response
            extractions = self._parse_response(response.content)
            extraction.extractions = extractions

        except LLMNotAvailableError:
            # Re-raise LLM availability errors - don't silently fail
            raise

        except Exception as e:
            logger.error(f"Extraction failed for {paper_id}: {e}")
            # Mark all fields as failed
            for field in self.schema.fields:
                extraction.extractions[field.key] = ExtractedValue(
                    value="EXTRACTION_FAILED",
                    confidence=0.0,
                )

        return extraction

    def extract_batch(
        self,
        papers: list[tuple[str, str, str | None, str | None]],
        progress_callback: Callable[[ExtractionProgress], None] | None = None,
    ) -> tuple[ExtractionMatrix, ExtractorResult]:
        """Extract evidence from multiple papers.

        Args:
            papers: List of (paper_id, content, title, bibtex_key) tuples.
            progress_callback: Optional callback for progress updates.

        Returns:
            Tuple of (ExtractionMatrix, ExtractorResult).
        """
        matrix = ExtractionMatrix(schema=self.schema)
        result = ExtractorResult()
        total = len(papers)

        for i, (paper_id, content, title, bibtex_key) in enumerate(papers):
            result.papers_processed += 1

            if progress_callback:
                progress_callback(
                    ExtractionProgress(
                        current=i + 1,
                        total=total,
                        paper_id=paper_id,
                        status="extracting",
                    )
                )

            try:
                extraction = self.extract(paper_id, content, title, bibtex_key)
                matrix.add_paper(extraction)
                result.papers_succeeded += 1

                if progress_callback:
                    progress_callback(
                        ExtractionProgress(
                            current=i + 1,
                            total=total,
                            paper_id=paper_id,
                            status="completed",
                        )
                    )

            except LLMNotAvailableError:
                # Re-raise LLM availability errors - don't silently fail
                raise

            except Exception as e:
                result.papers_failed += 1
                result.errors.append((paper_id, str(e)))
                logger.error(f"Failed to extract from {paper_id}: {e}")

                if progress_callback:
                    progress_callback(
                        ExtractionProgress(
                            current=i + 1,
                            total=total,
                            paper_id=paper_id,
                            status="failed",
                        )
                    )

        return matrix, result

    def extract_from_directory(
        self,
        markdown_dir: Path,
        progress_callback: Callable[[ExtractionProgress], None] | None = None,
    ) -> tuple[ExtractionMatrix, ExtractorResult]:
        """Extract evidence from all markdown files in a directory.

        Args:
            markdown_dir: Directory containing markdown files.
            progress_callback: Optional callback for progress updates.

        Returns:
            Tuple of (ExtractionMatrix, ExtractorResult).
        """
        markdown_dir = Path(markdown_dir)
        md_files = list(markdown_dir.glob("*.md"))

        papers = []
        for md_file in md_files:
            paper_id = md_file.stem
            try:
                content = md_file.read_text()
                # Try to extract title from first line
                title = self._extract_title_from_content(content)
                papers.append((paper_id, content, title, None))
            except Exception as e:
                logger.warning(f"Failed to read {md_file}: {e}")

        return self.extract_batch(papers, progress_callback)

    def _parse_response(self, response: str) -> dict[str, ExtractedValue]:
        """Parse LLM response into ExtractedValue objects.

        Args:
            response: Raw LLM response.

        Returns:
            Dictionary of field key -> ExtractedValue.
        """
        extractions: dict[str, ExtractedValue] = {}

        # Clean up response
        response = response.strip()

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()

        # Find JSON object
        if not response.startswith("{"):
            start = response.find("{")
            if start != -1:
                end = response.rfind("}") + 1
                response = response[start:end]

        try:
            data = json.loads(response)

            for key, value_data in data.items():
                if isinstance(value_data, dict):
                    extractions[key] = ExtractedValue(
                        value=value_data.get("value", "N/A"),
                        source_quote=value_data.get("quote"),
                        page_number=value_data.get("page"),
                    )
                else:
                    # Simple value
                    extractions[key] = ExtractedValue(value=value_data)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Try to extract values from the response text
            extractions = self._parse_fallback(response)

        # Validate and convert types
        extractions = self._validate_extractions(extractions)

        return extractions

    def _parse_fallback(self, response: str) -> dict[str, ExtractedValue]:
        """Fallback parser for non-JSON responses."""
        extractions: dict[str, ExtractedValue] = {}

        # Look for key: value patterns
        import re

        for field in self.schema.fields:
            pattern = rf"{field.key}[:\s]+([^\n]+)"
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Remove quotes
                value = value.strip("'\"")
                extractions[field.key] = ExtractedValue(value=value)

        return extractions

    def _validate_extractions(
        self, extractions: dict[str, ExtractedValue]
    ) -> dict[str, ExtractedValue]:
        """Validate and convert extraction types."""
        validated: dict[str, ExtractedValue] = {}

        for field in self.schema.fields:
            if field.key in extractions:
                ev = extractions[field.key]
                value = ev.value

                # Type conversion
                if field.type == FieldType.INTEGER and value != "N/A":
                    try:
                        # Extract number from text
                        import re

                        numbers = re.findall(r"[\d,]+", str(value))
                        if numbers:
                            value = int(numbers[0].replace(",", ""))
                    except (ValueError, TypeError):
                        pass

                elif field.type == FieldType.FLOAT and value != "N/A":
                    try:
                        import re

                        numbers = re.findall(r"[\d.,]+", str(value))
                        if numbers:
                            value = float(numbers[0].replace(",", ""))
                    except (ValueError, TypeError):
                        pass

                elif field.type == FieldType.BOOLEAN and value != "N/A":
                    value_str = str(value).lower()
                    if value_str in ("yes", "true", "1"):
                        value = True
                    elif value_str in ("no", "false", "0"):
                        value = False

                elif field.type == FieldType.CATEGORICAL and field.options:
                    # Try to match to valid option
                    value_str = str(value)
                    matched = None
                    for option in field.options:
                        if option.lower() == value_str.lower():
                            matched = option
                            break
                        if option.lower() in value_str.lower():
                            matched = option
                            break
                    if matched:
                        value = matched

                validated[field.key] = ExtractedValue(
                    value=value,
                    source_quote=ev.source_quote,
                    page_number=ev.page_number,
                    confidence=ev.confidence,
                )
            else:
                # Field not extracted
                validated[field.key] = ExtractedValue(value="N/A", confidence=0.0)

        return validated

    def _extract_title_from_content(self, content: str) -> str | None:
        """Extract title from markdown content."""
        lines = content.strip().split("\n")
        for line in lines[:5]:
            line = line.strip()
            # Check for markdown header
            if line.startswith("# "):
                return line[2:].strip()
            # Check for non-empty line
            if len(line) > 10 and len(line) < 200:
                return line
        return None


def extract_evidence(
    schema: ExtractionSchema,
    markdown_dir: Path,
    output_path: Path | None = None,
) -> ExtractionMatrix:
    """Convenience function to extract evidence from papers.

    Args:
        schema: Extraction schema.
        markdown_dir: Directory with markdown files.
        output_path: Optional path to save results.

    Returns:
        ExtractionMatrix with all extractions.
    """
    extractor = Extractor(schema)
    matrix, result = extractor.extract_from_directory(markdown_dir)

    if output_path:
        matrix.to_json(output_path)
        logger.info(f"Saved extraction matrix to {output_path}")

    logger.info(
        f"Extraction complete: {result.papers_succeeded}/{result.papers_processed} successful"
    )

    return matrix
