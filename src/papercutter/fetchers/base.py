"""Base class for paper fetchers."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Document:
    """Represents a fetched academic document."""

    path: Path
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    source_url: str | None = None
    fetched_at: datetime = field(default_factory=datetime.now)
    # Additional metadata from source (e.g., categories, published date)
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def exists(self) -> bool:
        """Check if the document file exists."""
        return self.path.exists()

    def to_metadata_dict(self) -> dict[str, Any]:
        """Convert document metadata to a dictionary for JSON export.

        Returns:
            Dictionary with all document metadata.
        """
        data = {
            "file": self.path.name,
            "fetched_at": self.fetched_at.isoformat(),
        }
        if self.title:
            data["title"] = self.title
        if self.authors:
            data["authors"] = self.authors
        if self.abstract:
            data["abstract"] = self.abstract
        if self.doi:
            data["doi"] = self.doi
        if self.arxiv_id:
            data["arxiv_id"] = self.arxiv_id
        if self.source_url:
            data["source_url"] = self.source_url
        if self.extra_metadata:
            data.update(self.extra_metadata)
        return data

    def save_metadata(self, output_path: Path | None = None) -> Path:
        """Save metadata as a JSON sidecar file.

        Args:
            output_path: Path for the metadata file. If None, uses
                        the PDF path with .meta.json extension.

        Returns:
            Path to the saved metadata file.
        """
        if output_path is None:
            output_path = self.path.with_suffix(".meta.json")

        metadata = self.to_metadata_dict()
        output_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
        return output_path


class BaseFetcher(ABC):
    """Abstract base class for paper fetchers."""

    @abstractmethod
    def can_handle(self, identifier: str) -> bool:
        """Check if this fetcher can handle the given identifier.

        Args:
            identifier: Paper identifier (ID, URL, DOI, etc.)

        Returns:
            True if this fetcher can handle the identifier.
        """
        pass

    @abstractmethod
    def fetch(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch the paper and return a Document.

        Args:
            identifier: Paper identifier.
            output_dir: Directory to save the downloaded PDF.
            **kwargs: Additional fetcher-specific options.

        Returns:
            Document object with path and metadata.
        """
        pass

    async def fetch_async(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch the paper asynchronously.

        Default implementation calls the synchronous fetch method.
        Override in subclasses for true async support.

        Args:
            identifier: Paper identifier.
            output_dir: Directory to save the downloaded PDF.
            **kwargs: Additional fetcher-specific options.

        Returns:
            Document object with path and metadata.
        """
        # Default: fallback to sync method (subclasses can override for true async)
        return self.fetch(identifier, output_dir, **kwargs)

    def normalize_id(self, identifier: str) -> str:
        """Normalize the identifier format.

        Override in subclasses if needed.

        Args:
            identifier: Raw identifier.

        Returns:
            Normalized identifier.
        """
        return identifier.strip()
