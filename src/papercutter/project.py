"""Project state management via inventory.json."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class Paper(BaseModel):
    """Represents a single paper in the project."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    filename: str
    markdown_path: str | None = None
    tables_path: str | None = None
    figures_path: str | None = None
    status: str = "pending"  # pending | ingested | extracted

    def get_markdown_path(self) -> Path | None:
        """Get markdown path as Path object."""
        return Path(self.markdown_path) if self.markdown_path else None

    def get_tables_path(self) -> Path | None:
        """Get tables path as Path object."""
        return Path(self.tables_path) if self.tables_path else None

    def get_figures_path(self) -> Path | None:
        """Get figures path as Path object."""
        return Path(self.figures_path) if self.figures_path else None


class Inventory(BaseModel):
    """Tracks all papers in the project."""

    papers: dict[str, Paper] = {}

    @classmethod
    def load(cls, project_dir: Path) -> Inventory:
        """Load inventory from project directory."""
        path = project_dir / "inventory.json"
        if path.exists():
            return cls.model_validate_json(path.read_text())
        return cls()

    def save(self, project_dir: Path) -> None:
        """Save inventory to project directory."""
        path = project_dir / "inventory.json"
        path.write_text(self.model_dump_json(indent=2))

    def add_paper(
        self,
        paper_id: str,
        filename: str,
        markdown_path: Path | None = None,
        tables_path: Path | None = None,
        figures_path: Path | None = None,
        status: str = "pending",
    ) -> Paper:
        """Add or update a paper in the inventory."""
        paper = Paper(
            id=paper_id,
            filename=filename,
            markdown_path=str(markdown_path) if markdown_path else None,
            tables_path=str(tables_path) if tables_path else None,
            figures_path=str(figures_path) if figures_path else None,
            status=status,
        )
        self.papers[paper_id] = paper
        return paper

    def get_by_status(self, status: str) -> list[Paper]:
        """Get all papers with a given status."""
        return [p for p in self.papers.values() if p.status == status]

    def count_by_status(self) -> dict[str, int]:
        """Count papers by status."""
        counts: dict[str, int] = {}
        for paper in self.papers.values():
            counts[paper.status] = counts.get(paper.status, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()
