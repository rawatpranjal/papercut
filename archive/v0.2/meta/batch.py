"""Batch extraction for meta-analysis across multiple papers."""

import csv
import json
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from papercutter.core.text import TextExtractor
from papercutter.extractors.pdfplumber import PdfPlumberExtractor
from papercutter.llm.client import LLMClient, get_client
from papercutter.llm.prompts import get_template


@dataclass
class ExtractionResult:
    """Result of extracting structured data from a paper."""

    source_path: Path
    data: dict[str, Any]
    success: bool = True
    error: Optional[str] = None

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested value from the extracted data.

        Args:
            *keys: Path of keys to traverse.
            default: Default value if not found.

        Returns:
            The value at the path, or default.
        """
        result = self.data
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        return result


@dataclass
class BatchResult:
    """Results from batch extraction across multiple papers."""

    results: list[ExtractionResult] = field(default_factory=list)

    @property
    def successful(self) -> list[ExtractionResult]:
        """Get successful extractions."""
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> list[ExtractionResult]:
        """Get failed extractions."""
        return [r for r in self.results if not r.success]

    def to_json(self, indent: int = 2) -> str:
        """Export all results to JSON.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string of all extraction results.
        """
        data = []
        for result in self.results:
            entry = {
                "source": str(result.source_path),
                "success": result.success,
            }
            if result.success:
                entry["data"] = result.data
            else:
                entry["error"] = result.error
            data.append(entry)

        return json.dumps(data, indent=indent)

    def to_csv(self) -> str:
        """Export successful results to flattened CSV.

        Flattens nested JSON structure into columns.

        Returns:
            CSV string of extraction results.
        """
        if not self.successful:
            return ""

        # Collect all unique column paths from all results
        columns = self._collect_columns()

        output = StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow(["source"] + columns)

        # Data rows
        for result in self.successful:
            row = [str(result.source_path)]
            for col in columns:
                value = self._get_nested(result.data, col)
                # Convert complex types to string
                if isinstance(value, (list, dict)):
                    value = json.dumps(value)
                elif value is None:
                    value = ""
                row.append(value)
            writer.writerow(row)

        return output.getvalue()

    def _collect_columns(self) -> list[str]:
        """Collect all unique column paths from results."""
        columns = set()
        for result in self.successful:
            self._flatten_keys(result.data, "", columns)
        return sorted(columns)

    def _flatten_keys(
        self, data: Any, prefix: str, columns: set[str]
    ) -> None:
        """Recursively collect flattened key paths."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    self._flatten_keys(value, new_prefix, columns)
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # List of objects - skip flattening
                    columns.add(new_prefix)
                else:
                    columns.add(new_prefix)

    def _get_nested(self, data: dict, path: str) -> Any:
        """Get a nested value using dot notation path."""
        keys = path.split(".")
        result = data
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return None
        return result


class BatchExtractor:
    """Extract structured meta-analysis data from multiple papers."""

    def __init__(
        self,
        model: Optional[str] = None,
        max_text_chars: int = 80000,
    ):
        """Initialize the batch extractor.

        Args:
            model: LLM model to use.
            max_text_chars: Maximum text characters per paper.
        """
        self.client = get_client(model)
        self.max_text_chars = max_text_chars
        self.text_extractor = TextExtractor(PdfPlumberExtractor())

    def extract_one(self, pdf_path: Path) -> ExtractionResult:
        """Extract meta-analysis data from a single paper.

        Args:
            pdf_path: Path to the PDF.

        Returns:
            ExtractionResult with structured data.
        """
        try:
            # Extract text
            text = self.text_extractor.extract(pdf_path)
            if len(text) > self.max_text_chars:
                text = text[: self.max_text_chars] + "\n\n[Truncated...]"

            # Get meta-analysis template
            template = get_template("meta_analysis")
            system, user = template.format(text=text)

            # Call LLM
            response = self.client.complete(
                system_prompt=system,
                user_prompt=user,
            )

            # Parse JSON response
            data = self._parse_json_response(response)

            return ExtractionResult(
                source_path=pdf_path,
                data=data,
                success=True,
            )

        except Exception as e:
            return ExtractionResult(
                source_path=pdf_path,
                data={},
                success=False,
                error=str(e),
            )

    def extract_batch(
        self,
        pdf_paths: list[Path],
        on_progress: Optional[callable] = None,
    ) -> BatchResult:
        """Extract meta-analysis data from multiple papers.

        Args:
            pdf_paths: List of PDF paths.
            on_progress: Optional callback(index, total, path) for progress.

        Returns:
            BatchResult with all extraction results.
        """
        results = []
        total = len(pdf_paths)

        for i, path in enumerate(pdf_paths):
            if on_progress:
                on_progress(i, total, path)

            result = self.extract_one(path)
            results.append(result)

        return BatchResult(results=results)

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from LLM response.

        Handles responses that may have markdown code blocks.

        Args:
            response: Raw LLM response.

        Returns:
            Parsed JSON data.

        Raises:
            ValueError: If JSON parsing fails.
        """
        # Strip markdown code blocks if present
        text = response.strip()

        if text.startswith("```"):
            # Remove opening code block
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # Try to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Failed to parse JSON: {e}")
