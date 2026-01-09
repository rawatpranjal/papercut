"""Paper inventory management for Papercutter Factory.

Tracks all papers in a project through the ingestion and extraction pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PaperStatus(str, Enum):
    """Processing status of a paper in the pipeline."""

    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"


class ExtractionMethod(str, Enum):
    """Method used to extract content from PDF."""

    DOCLING = "docling"
    OCR_FALLBACK = "ocr_fallback"


@dataclass
class PaperEntry:
    """A paper in the project inventory.

    Tracks a single PDF through the ingestion and extraction pipeline,
    including metadata, processing status, and extraction results.
    """

    id: str  # Hash-based unique ID
    filename: str  # Original filename
    path: str  # Relative path to PDF from project root

    # Metadata (from BibTeX match or LLM extraction)
    bibtex_key: str | None = None
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None

    # Processing status
    status: PaperStatus = PaperStatus.PENDING
    ingested_at: str | None = None  # ISO format datetime

    # Extraction results
    markdown_path: str | None = None  # Relative path to extracted .md
    tables_path: str | None = None  # Relative path to tables JSON
    extraction_method: ExtractionMethod | None = None

    # Sawmill tracking (for split books)
    is_split_child: bool = False
    parent_id: str | None = None  # Links "Chapter 1" back to parent book
    chapter_number: int | None = None
    chapter_title: str | None = None

    # Error tracking
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "filename": self.filename,
            "path": self.path,
            "bibtex_key": self.bibtex_key,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "status": self.status.value,
            "ingested_at": self.ingested_at,
            "markdown_path": self.markdown_path,
            "tables_path": self.tables_path,
            "extraction_method": self.extraction_method.value if self.extraction_method else None,
            "is_split_child": self.is_split_child,
            "parent_id": self.parent_id,
            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaperEntry:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            filename=data["filename"],
            path=data["path"],
            bibtex_key=data.get("bibtex_key"),
            title=data.get("title"),
            authors=data.get("authors", []),
            year=data.get("year"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            status=PaperStatus(data.get("status", "pending")),
            ingested_at=data.get("ingested_at"),
            markdown_path=data.get("markdown_path"),
            tables_path=data.get("tables_path"),
            extraction_method=(
                ExtractionMethod(data["extraction_method"])
                if data.get("extraction_method")
                else None
            ),
            is_split_child=data.get("is_split_child", False),
            parent_id=data.get("parent_id"),
            chapter_number=data.get("chapter_number"),
            chapter_title=data.get("chapter_title"),
            error_message=data.get("error_message"),
        )

    def mark_ingested(self, method: ExtractionMethod, markdown_path: str) -> None:
        """Mark paper as successfully ingested."""
        self.status = PaperStatus.INGESTED
        self.extraction_method = method
        self.markdown_path = markdown_path
        self.ingested_at = datetime.now().isoformat()
        self.error_message = None

    def mark_failed(self, error: str) -> None:
        """Mark paper as failed to ingest."""
        self.status = PaperStatus.FAILED
        self.error_message = error
        self.ingested_at = datetime.now().isoformat()


@dataclass
class ProjectInventory:
    """Complete project inventory tracking all papers.

    The inventory is stored in .papercutter/inventory.json and tracks
    all papers through the evidence synthesis pipeline.
    """

    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    papers: dict[str, PaperEntry] = field(default_factory=dict)  # id -> PaperEntry

    def add_paper(self, entry: PaperEntry) -> None:
        """Add a paper to the inventory."""
        self.papers[entry.id] = entry
        self.updated_at = datetime.now().isoformat()

    def get_paper(self, paper_id: str) -> PaperEntry | None:
        """Get a paper by ID."""
        return self.papers.get(paper_id)

    def remove_paper(self, paper_id: str) -> bool:
        """Remove a paper from the inventory."""
        if paper_id in self.papers:
            del self.papers[paper_id]
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def get_papers_by_status(self, status: PaperStatus) -> list[PaperEntry]:
        """Get all papers with a specific status."""
        return [p for p in self.papers.values() if p.status == status]

    def get_pending_papers(self) -> list[PaperEntry]:
        """Get all papers pending ingestion."""
        return self.get_papers_by_status(PaperStatus.PENDING)

    def get_ingested_papers(self) -> list[PaperEntry]:
        """Get all successfully ingested papers."""
        return self.get_papers_by_status(PaperStatus.INGESTED)

    def get_failed_papers(self) -> list[PaperEntry]:
        """Get all failed papers."""
        return self.get_papers_by_status(PaperStatus.FAILED)

    def get_children_of(self, parent_id: str) -> list[PaperEntry]:
        """Get all child papers (chapters) of a split book."""
        return [
            p for p in self.papers.values()
            if p.is_split_child and p.parent_id == parent_id
        ]

    @property
    def total_count(self) -> int:
        """Total number of papers in inventory."""
        return len(self.papers)

    @property
    def pending_count(self) -> int:
        """Number of pending papers."""
        return len(self.get_pending_papers())

    @property
    def ingested_count(self) -> int:
        """Number of ingested papers."""
        return len(self.get_ingested_papers())

    @property
    def failed_count(self) -> int:
        """Number of failed papers."""
        return len(self.get_failed_papers())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "papers": {pid: p.to_dict() for pid, p in self.papers.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectInventory:
        """Create from dictionary."""
        papers = {
            pid: PaperEntry.from_dict(pdata)
            for pid, pdata in data.get("papers", {}).items()
        }
        return cls(
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            papers=papers,
        )

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> ProjectInventory:
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
