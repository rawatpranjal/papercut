"""Extraction schema definition for Papercutter Factory.

Defines the schema for evidence extraction from academic papers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class FieldType(str, Enum):
    """Type of extraction field."""

    TEXT = "text"  # Free-form text
    INTEGER = "integer"  # Whole number
    FLOAT = "float"  # Decimal number
    BOOLEAN = "boolean"  # True/False
    CATEGORICAL = "categorical"  # One of predefined options
    LIST = "list"  # List of items


@dataclass
class SchemaField:
    """A field in the extraction schema.

    Defines what information to extract from each paper.
    """

    key: str
    """Unique identifier for this field (used as column name)."""

    description: str
    """Description of what to extract (used in LLM prompt)."""

    type: FieldType = FieldType.TEXT
    """Data type of the field."""

    required: bool = True
    """Whether this field must be extracted for every paper."""

    options: list[str] | None = None
    """Valid options for categorical fields."""

    example: str | None = None
    """Example value to guide extraction."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d: dict[str, Any] = {
            "key": self.key,
            "description": self.description,
            "type": self.type.value,
        }
        if not self.required:
            d["required"] = False
        if self.options:
            d["options"] = self.options
        if self.example:
            d["example"] = self.example
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaField:
        """Create from dictionary."""
        return cls(
            key=data["key"],
            description=data["description"],
            type=FieldType(data.get("type", "text")),
            required=data.get("required", True),
            options=data.get("options"),
            example=data.get("example"),
        )

    def to_prompt_line(self) -> str:
        """Generate a prompt line for LLM extraction."""
        parts = [f"- {self.key}: {self.description}"]

        if self.type == FieldType.CATEGORICAL and self.options:
            parts.append(f"  Options: {', '.join(self.options)}")
        elif self.type == FieldType.BOOLEAN:
            parts.append("  (yes/no)")
        elif self.type == FieldType.INTEGER:
            parts.append("  (integer)")
        elif self.type == FieldType.FLOAT:
            parts.append("  (number)")

        if self.example:
            parts.append(f"  Example: {self.example}")

        if not self.required:
            parts.append("  (optional)")

        return "\n".join(parts)


@dataclass
class ExtractionSchema:
    """Schema for evidence extraction from papers.

    Defines all fields to extract and how to extract them.
    """

    fields: list[SchemaField] = field(default_factory=list)
    """Fields to extract from each paper."""

    name: str = "Default Schema"
    """Name of this schema."""

    description: str = ""
    """Description of what this schema extracts."""

    version: str = "1.0"
    """Schema version for tracking changes."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "fields": [f.to_dict() for f in self.fields],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractionSchema:
        """Create from dictionary."""
        fields = [SchemaField.from_dict(f) for f in data.get("fields", [])]
        return cls(
            name=data.get("name", "Default Schema"),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            fields=fields,
        )

    def to_yaml(self) -> str:
        """Convert to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> ExtractionSchema:
        """Create from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data or {})

    def save(self, path: Path) -> None:
        """Save schema to YAML file."""
        path.write_text(self.to_yaml())

    @classmethod
    def load(cls, path: Path) -> ExtractionSchema:
        """Load schema from YAML file."""
        return cls.from_yaml(path.read_text())

    def to_extraction_prompt(self) -> str:
        """Generate the extraction prompt for LLM.

        Returns:
            Prompt string listing all fields to extract.
        """
        lines = ["Extract the following information from this paper:"]
        lines.append("")

        for f in self.fields:
            lines.append(f.to_prompt_line())

        lines.append("")
        lines.append(
            "If information is not found or not applicable, use 'N/A'. "
            "Provide direct quotes or page numbers where possible."
        )

        return "\n".join(lines)

    def add_field(
        self,
        key: str,
        description: str,
        field_type: FieldType = FieldType.TEXT,
        **kwargs: Any,
    ) -> SchemaField:
        """Add a new field to the schema.

        Args:
            key: Unique identifier for the field.
            description: What to extract.
            field_type: Data type.
            **kwargs: Additional field options.

        Returns:
            The created SchemaField.
        """
        f = SchemaField(
            key=key,
            description=description,
            type=field_type,
            **kwargs,
        )
        self.fields.append(f)
        return f

    def get_field(self, key: str) -> SchemaField | None:
        """Get a field by its key."""
        for f in self.fields:
            if f.key == key:
                return f
        return None

    def validate(self) -> list[str]:
        """Validate the schema and return any errors.

        Returns:
            List of validation error messages.
        """
        errors = []

        # Check for duplicate keys
        keys = [f.key for f in self.fields]
        duplicates = [k for k in keys if keys.count(k) > 1]
        if duplicates:
            errors.append(f"Duplicate field keys: {set(duplicates)}")

        # Check categorical fields have options
        for f in self.fields:
            if f.type == FieldType.CATEGORICAL and not f.options:
                errors.append(f"Categorical field '{f.key}' has no options")

        # Check for empty keys
        for f in self.fields:
            if not f.key.strip():
                errors.append("Found field with empty key")
            if not f.description.strip():
                errors.append(f"Field '{f.key}' has empty description")

        return errors


# Common schema templates
def create_economics_schema() -> ExtractionSchema:
    """Create a schema for economics papers."""
    schema = ExtractionSchema(
        name="Economics Research",
        description="Schema for extracting evidence from economics papers",
    )

    schema.add_field(
        "sample_size",
        "Number of observations, participants, or units in the study",
        FieldType.INTEGER,
        example="10,000 individuals",
    )
    schema.add_field(
        "time_period",
        "Time period covered by the data",
        FieldType.TEXT,
        example="2000-2020",
    )
    schema.add_field(
        "geography",
        "Geographic region or country studied",
        FieldType.TEXT,
        example="United States",
    )
    schema.add_field(
        "methodology",
        "Primary identification or estimation strategy",
        FieldType.CATEGORICAL,
        options=["DiD", "RDD", "IV", "OLS", "RCT", "Event Study", "Other"],
    )
    schema.add_field(
        "main_finding",
        "Primary quantitative result or effect size",
        FieldType.TEXT,
        example="10% increase leads to 5% decrease in X",
    )
    schema.add_field(
        "data_source",
        "Source of the data used in the analysis",
        FieldType.TEXT,
        example="Census Bureau ACS",
    )

    return schema


def create_medical_schema() -> ExtractionSchema:
    """Create a schema for medical/clinical papers."""
    schema = ExtractionSchema(
        name="Medical Research",
        description="Schema for extracting evidence from medical papers",
    )

    schema.add_field(
        "study_type",
        "Type of study design",
        FieldType.CATEGORICAL,
        options=["RCT", "Cohort", "Case-Control", "Cross-Sectional", "Meta-Analysis", "Other"],
    )
    schema.add_field(
        "sample_size",
        "Number of participants",
        FieldType.INTEGER,
    )
    schema.add_field(
        "intervention",
        "Treatment or intervention studied",
        FieldType.TEXT,
    )
    schema.add_field(
        "control",
        "Control or comparison group",
        FieldType.TEXT,
    )
    schema.add_field(
        "primary_outcome",
        "Main outcome measure",
        FieldType.TEXT,
    )
    schema.add_field(
        "effect_size",
        "Primary effect size with confidence interval",
        FieldType.TEXT,
        example="OR 1.5 (95% CI: 1.2-1.8)",
    )
    schema.add_field(
        "follow_up",
        "Duration of follow-up",
        FieldType.TEXT,
        example="12 months",
    )

    return schema
