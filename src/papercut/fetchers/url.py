"""Direct URL fetcher."""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from papercut.exceptions import FetchError
from papercut.fetchers.base import BaseFetcher, Document
from papercut.utils.http import download_file


class URLFetcher(BaseFetcher):
    """Fetch papers from direct URLs."""

    # Pattern to match URLs
    URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)

    def can_handle(self, identifier: str) -> bool:
        """Check if this fetcher can handle the given identifier."""
        return bool(self.URL_PATTERN.match(identifier.strip()))

    def fetch(
        self,
        identifier: str,
        output_dir: Path,
        name: Optional[str] = None,
        **kwargs,
    ) -> Document:
        """Download paper from URL.

        Args:
            identifier: URL to download from.
            output_dir: Directory to save the downloaded PDF.
            name: Optional custom filename (without extension).

        Returns:
            Document object with path.

        Raises:
            FetchError: If download fails.
        """
        url = identifier.strip()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename
        if name:
            filename = f"{name}.pdf"
        else:
            filename = self._filename_from_url(url)

        try:
            pdf_path = download_file(url, output_dir, filename)
            return Document(
                path=pdf_path,
                source_url=url,
            )
        except Exception as e:
            raise FetchError(
                f"Failed to download from URL",
                details=str(e),
            ) from e

    def _filename_from_url(self, url: str) -> str:
        """Extract filename from URL.

        Args:
            url: URL to extract filename from.

        Returns:
            Filename string.
        """
        parsed = urlparse(url)
        path = Path(parsed.path)

        if path.suffix.lower() == ".pdf":
            # Use the filename from URL
            name = path.stem
            # Clean up the name
            name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
            return f"{name}.pdf"

        # Fallback: use domain and path hash
        domain = parsed.netloc.replace(".", "_")
        return f"{domain}_download.pdf"
