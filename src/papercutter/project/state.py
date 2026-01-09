"""Project configuration state for Papercutter Factory.

Handles project-level configuration stored in .papercutter/config.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml


@dataclass
class SchemaColumn:
    """A column in the extraction schema."""

    key: str
    description: str
    type: Literal["text", "integer", "float", "boolean", "categorical", "list"] = "text"
    required: bool = True
    options: list[str] | None = None  # For categorical type
    example: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d: dict[str, Any] = {
            "key": self.key,
            "description": self.description,
            "type": self.type,
            "required": self.required,
        }
        if self.options:
            d["options"] = self.options
        if self.example:
            d["example"] = self.example
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaColumn:
        """Create from dictionary."""
        return cls(
            key=data["key"],
            description=data["description"],
            type=data.get("type", "text"),
            required=data.get("required", True),
            options=data.get("options"),
            example=data.get("example"),
        )


@dataclass
class GrindingConfig:
    """Configuration for evidence extraction (grinding phase)."""

    columns: list[SchemaColumn] = field(default_factory=list)
    model: str = "claude-sonnet-4-20250514"
    max_context_chars: int = 100000  # Max chars to send to LLM per paper

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "columns": [c.to_dict() for c in self.columns],
            "model": self.model,
            "max_context_chars": self.max_context_chars,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GrindingConfig:
        """Create from dictionary."""
        columns = [SchemaColumn.from_dict(c) for c in data.get("columns", [])]
        return cls(
            columns=columns,
            model=data.get("model", "claude-sonnet-4-20250514"),
            max_context_chars=data.get("max_context_chars", 100000),
        )


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    template: str = "default"
    output_format: Literal["latex", "markdown"] = "latex"
    bibliography_style: str = "apa"
    include_summaries: bool = True
    include_matrix: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template": self.template,
            "output_format": self.output_format,
            "bibliography_style": self.bibliography_style,
            "include_summaries": self.include_summaries,
            "include_matrix": self.include_matrix,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReportConfig:
        """Create from dictionary."""
        return cls(
            template=data.get("template", "default"),
            output_format=data.get("output_format", "latex"),
            bibliography_style=data.get("bibliography_style", "apa"),
            include_summaries=data.get("include_summaries", True),
            include_matrix=data.get("include_matrix", True),
        )


@dataclass
class ProjectConfig:
    """Project-level configuration.

    Stored in .papercutter/config.yaml.
    """

    name: str = "Untitled Project"
    bibtex_path: str | None = None  # Relative path to .bib file

    # Sawmill settings
    split_threshold_pages: int = 500  # Split books larger than this

    # Pipeline configurations
    grinding: GrindingConfig = field(default_factory=GrindingConfig)
    reporting: ReportConfig = field(default_factory=ReportConfig)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "bibtex_path": self.bibtex_path,
            "split_threshold_pages": self.split_threshold_pages,
            "grinding": self.grinding.to_dict(),
            "reporting": self.reporting.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectConfig:
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Untitled Project"),
            bibtex_path=data.get("bibtex_path"),
            split_threshold_pages=data.get("split_threshold_pages", 500),
            grinding=GrindingConfig.from_dict(data.get("grinding", {})),
            reporting=ReportConfig.from_dict(data.get("reporting", {})),
        )

    def to_yaml(self) -> str:
        """Convert to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> ProjectConfig:
        """Create from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data or {})

    def save(self, path: Path) -> None:
        """Save configuration to YAML file."""
        path.write_text(self.to_yaml())

    @classmethod
    def load(cls, path: Path) -> ProjectConfig:
        """Load configuration from YAML file."""
        return cls.from_yaml(path.read_text())
