"""File-based cache store for PDF extractions."""

import json
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from papercut.cache.hash import file_hash


class CacheStore:
    """File-based cache for PDF extraction results.

    Cache structure:
        ~/.cache/papercut/
        ├── <hash>/
        │   ├── index.json      # Document index
        │   ├── pages/
        │   │   ├── 001-005.txt # Page range text
        │   │   └── 010-014.txt
        │   ├── tables/
        │   │   └── table_3.json
        │   └── figures/
        │       └── fig_1.png
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the cache store.

        Args:
            cache_dir: Cache directory path. Defaults to ~/.cache/papercut/
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "papercut"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, pdf_path: Path) -> Path:
        """Get the cache directory for a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Path to the cache directory for this file.
        """
        hash_key = file_hash(pdf_path)
        return self.cache_dir / hash_key

    def has_cache(self, pdf_path: Path) -> bool:
        """Check if a PDF has cached data.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            True if cache exists for this file.
        """
        cache_path = self.get_cache_path(pdf_path)
        return cache_path.exists()

    def has_index(self, pdf_path: Path) -> bool:
        """Check if index is cached.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            True if index.json exists in cache.
        """
        index_path = self.get_cache_path(pdf_path) / "index.json"
        return index_path.exists()

    def get_index(self, pdf_path: Path) -> Optional[dict[str, Any]]:
        """Get cached index for a PDF.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Index dict or None if not cached.
        """
        index_path = self.get_cache_path(pdf_path) / "index.json"
        if not index_path.exists():
            return None

        with open(index_path) as f:
            return json.load(f)

    def set_index(self, pdf_path: Path, index: dict[str, Any]) -> None:
        """Cache index for a PDF.

        Args:
            pdf_path: Path to the PDF file.
            index: Index dict to cache.
        """
        cache_path = self.get_cache_path(pdf_path)
        cache_path.mkdir(parents=True, exist_ok=True)

        index_path = cache_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)

    def has_pages(self, pdf_path: Path, start: int, end: int) -> bool:
        """Check if page range is cached.

        Args:
            pdf_path: Path to the PDF file.
            start: Start page (1-indexed).
            end: End page (1-indexed, inclusive).

        Returns:
            True if this page range is cached.
        """
        pages_path = self._pages_path(pdf_path, start, end)
        return pages_path.exists()

    def get_pages(self, pdf_path: Path, start: int, end: int) -> Optional[str]:
        """Get cached text for a page range.

        Args:
            pdf_path: Path to the PDF file.
            start: Start page (1-indexed).
            end: End page (1-indexed, inclusive).

        Returns:
            Cached text or None if not cached.
        """
        pages_path = self._pages_path(pdf_path, start, end)
        if not pages_path.exists():
            return None

        return pages_path.read_text()

    def set_pages(self, pdf_path: Path, start: int, end: int, text: str) -> None:
        """Cache text for a page range.

        Args:
            pdf_path: Path to the PDF file.
            start: Start page (1-indexed).
            end: End page (1-indexed, inclusive).
            text: Text content to cache.
        """
        pages_dir = self.get_cache_path(pdf_path) / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        pages_path = self._pages_path(pdf_path, start, end)
        pages_path.write_text(text)

    def _pages_path(self, pdf_path: Path, start: int, end: int) -> Path:
        """Get path for cached page range file."""
        return self.get_cache_path(pdf_path) / "pages" / f"{start:03d}-{end:03d}.txt"

    def has_table(self, pdf_path: Path, table_id: int) -> bool:
        """Check if table is cached.

        Args:
            pdf_path: Path to the PDF file.
            table_id: Table ID.

        Returns:
            True if this table is cached.
        """
        table_path = self._table_path(pdf_path, table_id)
        return table_path.exists()

    def get_table(self, pdf_path: Path, table_id: int) -> Optional[dict[str, Any]]:
        """Get cached table.

        Args:
            pdf_path: Path to the PDF file.
            table_id: Table ID.

        Returns:
            Table dict or None if not cached.
        """
        table_path = self._table_path(pdf_path, table_id)
        if not table_path.exists():
            return None

        with open(table_path) as f:
            return json.load(f)

    def set_table(self, pdf_path: Path, table_id: int, table: dict[str, Any]) -> None:
        """Cache table.

        Args:
            pdf_path: Path to the PDF file.
            table_id: Table ID.
            table: Table dict to cache.
        """
        tables_dir = self.get_cache_path(pdf_path) / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)

        table_path = self._table_path(pdf_path, table_id)
        with open(table_path, "w") as f:
            json.dump(table, f, indent=2)

    def _table_path(self, pdf_path: Path, table_id: int) -> Path:
        """Get path for cached table file."""
        return self.get_cache_path(pdf_path) / "tables" / f"table_{table_id}.json"

    def has_figure(self, pdf_path: Path, figure_id: int) -> bool:
        """Check if figure is cached.

        Args:
            pdf_path: Path to the PDF file.
            figure_id: Figure ID.

        Returns:
            True if this figure is cached.
        """
        figure_path = self._figure_path(pdf_path, figure_id)
        return figure_path.exists()

    def get_figure_path(self, pdf_path: Path, figure_id: int) -> Optional[Path]:
        """Get path to cached figure.

        Args:
            pdf_path: Path to the PDF file.
            figure_id: Figure ID.

        Returns:
            Path to cached figure or None if not cached.
        """
        figure_path = self._figure_path(pdf_path, figure_id)
        if not figure_path.exists():
            return None
        return figure_path

    def set_figure(self, pdf_path: Path, figure_id: int, image_data: bytes) -> Path:
        """Cache figure.

        Args:
            pdf_path: Path to the PDF file.
            figure_id: Figure ID.
            image_data: Image bytes to cache.

        Returns:
            Path to cached figure.
        """
        figures_dir = self.get_cache_path(pdf_path) / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)

        figure_path = self._figure_path(pdf_path, figure_id)
        figure_path.write_bytes(image_data)
        return figure_path

    def _figure_path(self, pdf_path: Path, figure_id: int) -> Path:
        """Get path for cached figure file."""
        return self.get_cache_path(pdf_path) / "figures" / f"fig_{figure_id}.png"

    def clear(self, pdf_path: Optional[Path] = None) -> None:
        """Clear cache.

        Args:
            pdf_path: If provided, clear cache for this file only.
                     If None, clear entire cache.
        """
        if pdf_path is not None:
            cache_path = self.get_cache_path(pdf_path)
            if cache_path.exists():
                shutil.rmtree(cache_path)
        else:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)

    def cache_info(self, pdf_path: Path) -> dict[str, Any]:
        """Get cache info for a PDF.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Dict with cache status info.
        """
        cache_path = self.get_cache_path(pdf_path)

        info = {
            "cached": cache_path.exists(),
            "cache_path": str(cache_path),
            "hash": file_hash(pdf_path),
        }

        if cache_path.exists():
            info["has_index"] = (cache_path / "index.json").exists()

            pages_dir = cache_path / "pages"
            info["cached_pages"] = (
                len(list(pages_dir.glob("*.txt"))) if pages_dir.exists() else 0
            )

            tables_dir = cache_path / "tables"
            info["cached_tables"] = (
                len(list(tables_dir.glob("*.json"))) if tables_dir.exists() else 0
            )

            figures_dir = cache_path / "figures"
            info["cached_figures"] = (
                len(list(figures_dir.glob("*.png"))) if figures_dir.exists() else 0
            )

        return info


@lru_cache(maxsize=1)
def get_cache(cache_dir: Optional[str] = None) -> CacheStore:
    """Get the global cache store instance.

    Args:
        cache_dir: Optional cache directory path.

    Returns:
        CacheStore instance.
    """
    return CacheStore(Path(cache_dir) if cache_dir else None)
