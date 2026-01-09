"""Extraction matrix for Papercutter Factory.

Holds all paper extractions in a structured format with support
for export to CSV, JSON, and pandas DataFrame.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from papercutter.grinding.schema import ExtractionSchema, FieldType

logger = logging.getLogger(__name__)


@dataclass
class ExtractedValue:
    """A single extracted value with provenance."""

    value: Any
    """The extracted value."""

    source_quote: str | None = None
    """Direct quote from the paper supporting this value."""

    page_number: int | None = None
    """Page number where the value was found."""

    confidence: float = 1.0
    """Confidence score (0-1) for this extraction."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d: dict[str, Any] = {"value": self.value}
        if self.source_quote:
            d["source_quote"] = self.source_quote
        if self.page_number:
            d["page"] = self.page_number
        if self.confidence < 1.0:
            d["confidence"] = self.confidence
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractedValue:
        """Create from dictionary."""
        if isinstance(data, dict) and "value" in data:
            return cls(
                value=data["value"],
                source_quote=data.get("source_quote"),
                page_number=data.get("page"),
                confidence=data.get("confidence", 1.0),
            )
        # Simple value without metadata
        return cls(value=data)


@dataclass
class PaperExtraction:
    """Extraction results for a single paper."""

    paper_id: str
    """Unique identifier for the paper."""

    title: str | None = None
    """Paper title."""

    bibtex_key: str | None = None
    """BibTeX citation key."""

    extractions: dict[str, ExtractedValue] = field(default_factory=dict)
    """Map of field key -> extracted value."""

    # Synthesis outputs
    one_pager: str | None = None
    """Detailed summary (2500 chars max)."""

    appendix_row: str | None = None
    """Short contribution statement (350 chars max)."""

    def get_value(self, key: str) -> Any:
        """Get the raw value for a field."""
        if key in self.extractions:
            return self.extractions[key].value
        return None

    def set_value(
        self,
        key: str,
        value: Any,
        source_quote: str | None = None,
        page_number: int | None = None,
    ) -> None:
        """Set an extracted value."""
        self.extractions[key] = ExtractedValue(
            value=value,
            source_quote=source_quote,
            page_number=page_number,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "bibtex_key": self.bibtex_key,
            "extractions": {k: v.to_dict() for k, v in self.extractions.items()},
            "one_pager": self.one_pager,
            "appendix_row": self.appendix_row,
        }

    def to_flat_dict(self) -> dict[str, Any]:
        """Convert to flat dictionary for CSV export."""
        d: dict[str, Any] = {
            "paper_id": self.paper_id,
            "title": self.title or "",
            "bibtex_key": self.bibtex_key or "",
        }
        for key, extracted in self.extractions.items():
            d[key] = extracted.value
        d["one_pager"] = self.one_pager or ""
        d["appendix_row"] = self.appendix_row or ""
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaperExtraction:
        """Create from dictionary."""
        extractions = {}
        for key, value in data.get("extractions", {}).items():
            extractions[key] = ExtractedValue.from_dict(value)

        return cls(
            paper_id=data["paper_id"],
            title=data.get("title"),
            bibtex_key=data.get("bibtex_key"),
            extractions=extractions,
            one_pager=data.get("one_pager"),
            appendix_row=data.get("appendix_row"),
        )


class ExtractionMatrix:
    """Matrix holding all paper extractions.

    Provides structured storage and export for extraction results
    from all papers in a project.
    """

    def __init__(self, schema: ExtractionSchema | None = None):
        """Initialize the matrix.

        Args:
            schema: Extraction schema defining the fields.
        """
        self.schema = schema
        self._papers: dict[str, PaperExtraction] = {}

    @property
    def paper_count(self) -> int:
        """Number of papers in the matrix."""
        return len(self._papers)

    @property
    def field_keys(self) -> list[str]:
        """List of field keys from schema."""
        if self.schema:
            return [f.key for f in self.schema.fields]
        # Infer from extractions
        keys: set[str] = set()
        for paper in self._papers.values():
            keys.update(paper.extractions.keys())
        return sorted(keys)

    def add_paper(self, extraction: PaperExtraction) -> None:
        """Add a paper extraction to the matrix."""
        self._papers[extraction.paper_id] = extraction

    def get_paper(self, paper_id: str) -> PaperExtraction | None:
        """Get extraction for a specific paper."""
        return self._papers.get(paper_id)

    def remove_paper(self, paper_id: str) -> bool:
        """Remove a paper from the matrix."""
        if paper_id in self._papers:
            del self._papers[paper_id]
            return True
        return False

    def __iter__(self) -> Iterator[PaperExtraction]:
        """Iterate over paper extractions."""
        return iter(self._papers.values())

    def __len__(self) -> int:
        """Number of papers."""
        return len(self._papers)

    def to_dict(self) -> dict[str, Any]:
        """Convert entire matrix to dictionary."""
        return {
            "schema": self.schema.to_dict() if self.schema else None,
            "papers": [p.to_dict() for p in self._papers.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractionMatrix:
        """Create from dictionary."""
        schema = None
        if data.get("schema"):
            schema = ExtractionSchema.from_dict(data["schema"])

        matrix = cls(schema=schema)
        for paper_data in data.get("papers", []):
            matrix.add_paper(PaperExtraction.from_dict(paper_data))

        return matrix

    def to_json(self, path: Path | None = None, indent: int = 2) -> str:
        """Export to JSON.

        Args:
            path: Optional path to save to.
            indent: JSON indentation.

        Returns:
            JSON string.
        """
        json_str = json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
        if path:
            path.write_text(json_str)
        return json_str

    @classmethod
    def from_json(cls, path: Path) -> ExtractionMatrix:
        """Load from JSON file."""
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    def to_csv(self, path: Path) -> None:
        """Export to CSV file.

        Args:
            path: Path to save CSV.
        """
        if not self._papers:
            return

        # Build header
        header = ["paper_id", "title", "bibtex_key"]
        header.extend(self.field_keys)
        header.extend(["one_pager", "appendix_row"])

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
            writer.writeheader()

            for paper in self._papers.values():
                writer.writerow(paper.to_flat_dict())

    @classmethod
    def from_csv(cls, path: Path) -> ExtractionMatrix:
        """Load from CSV file."""
        matrix = cls()

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_id = row.pop("paper_id", "")
                title = row.pop("title", None)
                bibtex_key = row.pop("bibtex_key", None)
                one_pager = row.pop("one_pager", None)
                appendix_row = row.pop("appendix_row", None)

                extraction = PaperExtraction(
                    paper_id=paper_id,
                    title=title or None,
                    bibtex_key=bibtex_key or None,
                    one_pager=one_pager or None,
                    appendix_row=appendix_row or None,
                )

                # Remaining columns are extractions
                for key, value in row.items():
                    if value:  # Skip empty values
                        extraction.set_value(key, value)

                matrix.add_paper(extraction)

        return matrix

    def to_dataframe(self):
        """Export to pandas DataFrame.

        Returns:
            pandas.DataFrame with all extractions.

        Raises:
            ImportError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrame export. "
                "Install with: pip install pandas"
            )

        rows = [paper.to_flat_dict() for paper in self._papers.values()]
        return pd.DataFrame(rows)

    def get_column_values(self, key: str) -> list[Any]:
        """Get all values for a specific column.

        Args:
            key: Field key.

        Returns:
            List of values (may contain None).
        """
        return [paper.get_value(key) for paper in self._papers.values()]

    def get_column_stats(self, key: str) -> dict[str, Any]:
        """Get statistics for a column.

        Args:
            key: Field key.

        Returns:
            Statistics dictionary.
        """
        values = [v for v in self.get_column_values(key) if v is not None]
        stats: dict[str, Any] = {
            "total": len(self._papers),
            "non_null": len(values),
            "null": len(self._papers) - len(values),
        }

        # Type-specific stats
        if self.schema:
            field = self.schema.get_field(key)
            if field:
                if field.type in (FieldType.INTEGER, FieldType.FLOAT):
                    numeric_values = []
                    for v in values:
                        try:
                            numeric_values.append(float(v))
                        except (ValueError, TypeError):
                            pass
                    if numeric_values:
                        stats["min"] = min(numeric_values)
                        stats["max"] = max(numeric_values)
                        stats["mean"] = sum(numeric_values) / len(numeric_values)

                elif field.type == FieldType.CATEGORICAL:
                    value_counts: dict[str, int] = {}
                    for v in values:
                        v_str = str(v)
                        value_counts[v_str] = value_counts.get(v_str, 0) + 1
                    stats["value_counts"] = value_counts

        return stats

    def validate(self) -> list[str]:
        """Validate the matrix against the schema.

        Returns:
            List of validation warnings.
        """
        warnings = []

        if not self.schema:
            return warnings

        for paper in self._papers.values():
            for field in self.schema.fields:
                if field.required:
                    value = paper.get_value(field.key)
                    if value is None or value == "" or value == "N/A":
                        warnings.append(
                            f"Paper {paper.paper_id}: Missing required field '{field.key}'"
                        )

                # Check categorical values
                if field.type == FieldType.CATEGORICAL and field.options:
                    value = paper.get_value(field.key)
                    if value and str(value) not in field.options:
                        warnings.append(
                            f"Paper {paper.paper_id}: Invalid value '{value}' "
                            f"for categorical field '{field.key}'"
                        )

        return warnings

    def summary(self) -> dict[str, Any]:
        """Generate a summary of the matrix.

        Returns:
            Summary dictionary.
        """
        summary: dict[str, Any] = {
            "paper_count": len(self._papers),
            "field_count": len(self.field_keys),
            "fields": {},
        }

        for key in self.field_keys:
            stats = self.get_column_stats(key)
            summary["fields"][key] = {
                "completeness": (
                    f"{stats['non_null']}/{stats['total']} "
                    f"({100 * stats['non_null'] / max(stats['total'], 1):.0f}%)"
                ),
            }

        return summary
