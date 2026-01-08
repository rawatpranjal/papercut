"""Base class for paper fetchers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Document:
    """Represents a fetched academic document."""

    path: Path
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    source_url: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def exists(self) -> bool:
        """Check if the document file exists."""
        return self.path.exists()


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

    def normalize_id(self, identifier: str) -> str:
        """Normalize the identifier format.

        Override in subclasses if needed.

        Args:
            identifier: Raw identifier.

        Returns:
            Normalized identifier.
        """
        return identifier.strip()
