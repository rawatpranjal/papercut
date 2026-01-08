"""File-based cache store for PDF extractions."""

import json
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any

from papercutter.cache.hash import file_hash


class CacheStore:
    """File-based cache for PDF extraction results.

    Cache structure:
        ~/.cache/papercutter/
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

    def __init__(self, cache_dir: Path | None = None):
        """Initialize the cache store.

        Args:
            cache_dir: Cache directory path. Defaults to ~/.cache/papercutter/
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "papercutter"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_json_write(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON data atomically using temp file + rename.

        This prevents cache corruption if the process is interrupted mid-write.

        Args:
            path: Target file path.
            data: JSON-serializable data.
        """
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        tmp_path.rename(path)  # Atomic on POSIX systems

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

    def get_index(self, pdf_path: Path) -> dict[str, Any] | None:
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

        Uses atomic write (temp file + rename) to prevent corruption.

        Args:
            pdf_path: Path to the PDF file.
            index: Index dict to cache.
        """
        cache_path = self.get_cache_path(pdf_path)
        cache_path.mkdir(parents=True, exist_ok=True)

        index_path = cache_path / "index.json"
        self._atomic_json_write(index_path, index)

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

    def get_pages(self, pdf_path: Path, start: int, end: int) -> str | None:
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

    def get_table(self, pdf_path: Path, table_id: int) -> dict[str, Any] | None:
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

        Uses atomic write to prevent corruption.

        Args:
            pdf_path: Path to the PDF file.
            table_id: Table ID.
            table: Table dict to cache.
        """
        tables_dir = self.get_cache_path(pdf_path) / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)

        table_path = self._table_path(pdf_path, table_id)
        self._atomic_json_write(table_path, table)

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

    def get_figure_path(self, pdf_path: Path, figure_id: int) -> Path | None:
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

    def has_equation(self, pdf_path: Path, equation_id: int) -> bool:
        """Check if equation is cached.

        Args:
            pdf_path: Path to the PDF file.
            equation_id: Equation ID.

        Returns:
            True if this equation is cached.
        """
        equation_path = self._equation_path(pdf_path, equation_id)
        return equation_path.exists()

    def get_equation_path(self, pdf_path: Path, equation_id: int) -> Path | None:
        """Get path to cached equation image.

        Args:
            pdf_path: Path to the PDF file.
            equation_id: Equation ID.

        Returns:
            Path to cached equation or None if not cached.
        """
        equation_path = self._equation_path(pdf_path, equation_id)
        if not equation_path.exists():
            return None
        return equation_path

    def set_equation(self, pdf_path: Path, equation_id: int, image_data: bytes) -> Path:
        """Cache equation image.

        Args:
            pdf_path: Path to the PDF file.
            equation_id: Equation ID.
            image_data: Image bytes to cache.

        Returns:
            Path to cached equation.
        """
        equations_dir = self.get_cache_path(pdf_path) / "equations"
        equations_dir.mkdir(parents=True, exist_ok=True)

        equation_path = self._equation_path(pdf_path, equation_id)
        equation_path.write_bytes(image_data)
        return equation_path

    def get_equation_latex(self, pdf_path: Path, equation_id: int) -> dict[str, Any] | None:
        """Get cached LaTeX conversion for equation.

        Args:
            pdf_path: Path to the PDF file.
            equation_id: Equation ID.

        Returns:
            LaTeX dict or None if not cached.
        """
        latex_path = self._equation_latex_path(pdf_path, equation_id)
        if not latex_path.exists():
            return None

        with open(latex_path) as f:
            return json.load(f)

    def set_equation_latex(
        self, pdf_path: Path, equation_id: int, latex_data: dict[str, Any]
    ) -> None:
        """Cache LaTeX conversion for equation.

        Uses atomic write to prevent corruption.

        Args:
            pdf_path: Path to the PDF file.
            equation_id: Equation ID.
            latex_data: LaTeX conversion dict to cache.
        """
        equations_dir = self.get_cache_path(pdf_path) / "equations"
        equations_dir.mkdir(parents=True, exist_ok=True)

        latex_path = self._equation_latex_path(pdf_path, equation_id)
        self._atomic_json_write(latex_path, latex_data)

    def _equation_path(self, pdf_path: Path, equation_id: int) -> Path:
        """Get path for cached equation image file."""
        return self.get_cache_path(pdf_path) / "equations" / f"eq_{equation_id}.png"

    def _equation_latex_path(self, pdf_path: Path, equation_id: int) -> Path:
        """Get path for cached equation LaTeX file."""
        return self.get_cache_path(pdf_path) / "equations" / f"eq_{equation_id}.json"

    def clear(self, pdf_path: Path | None = None) -> None:
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

        Uses efficient single-pass directory iteration instead of multiple globs.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Dict with cache status info.
        """
        cache_path = self.get_cache_path(pdf_path)

        info: dict[str, Any] = {
            "cached": cache_path.exists(),
            "cache_path": str(cache_path),
            "hash": file_hash(pdf_path),
        }

        if cache_path.exists():
            info["has_index"] = (cache_path / "index.json").exists()

            # Efficient single-pass counting for each subdirectory
            cache_counts = {
                "pages": (".txt", "cached_pages"),
                "tables": (".json", "cached_tables"),
                "figures": (".png", "cached_figures"),
                "equations": (".png", "cached_equations"),
            }

            for subdir, (ext, info_key) in cache_counts.items():
                dir_path = cache_path / subdir
                if dir_path.exists():
                    # Use iterdir() instead of glob() - faster for counting
                    count = sum(1 for f in dir_path.iterdir() if f.suffix == ext)
                    info[info_key] = count
                else:
                    info[info_key] = 0

        return info


@lru_cache(maxsize=1)
def get_cache(cache_dir: str | None = None) -> CacheStore:
    """Get the global cache store instance.

    Args:
        cache_dir: Optional cache directory path.

    Returns:
        CacheStore instance.
    """
    return CacheStore(Path(cache_dir) if cache_dir else None)
