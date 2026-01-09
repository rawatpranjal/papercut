"""Direct URL fetcher."""

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from papercutter.exceptions import FetchError
from papercutter.legacy.fetchers.base import BaseFetcher, Document
from papercutter.utils.http import download_file, download_file_async


def _sanitize_name(name: str) -> str:
    """Sanitize a user-provided name to prevent path traversal.

    Args:
        name: The name to sanitize (without extension).

    Returns:
        A safe name with path traversal attempts removed.
    """
    # URL-decode to catch encoded traversal attempts
    name = unquote(name)
    # Get just the basename, stripping any path components
    name = os.path.basename(name)
    # Remove leading dots
    name = name.lstrip(".")
    # Only allow safe characters
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    # Ensure non-empty
    if not name:
        name = "download"
    # Limit length
    return name[:200]


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
        name: str | None = None,
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

        # Determine filename (sanitize user-provided name)
        if name:
            safe_name = _sanitize_name(name)
            filename = f"{safe_name}.pdf"
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
                "Failed to download from URL",
                details=str(e),
            ) from e

    async def fetch_async(
        self,
        identifier: str,
        output_dir: Path,
        name: str | None = None,
        **kwargs,
    ) -> Document:
        """Download paper from URL asynchronously.

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

        # Determine filename (sanitize user-provided name)
        if name:
            safe_name = _sanitize_name(name)
            filename = f"{safe_name}.pdf"
        else:
            filename = self._filename_from_url(url)

        try:
            pdf_path = await download_file_async(url, output_dir, filename)
            return Document(
                path=pdf_path,
                source_url=url,
            )
        except Exception as e:
            raise FetchError(
                "Failed to download from URL",
                details=str(e),
            ) from e

    # Patterns for extracting paper IDs from common academic URLs
    _PAPER_ID_PATTERNS = [
        # arXiv: https://arxiv.org/pdf/2301.00001 or /abs/2301.00001
        (re.compile(r"arxiv\.org/(?:pdf|abs)/(\d{4}\.\d{4,5})"), "arxiv_{}.pdf"),
        # arXiv old format: hep-th/9901001
        (re.compile(r"arxiv\.org/(?:pdf|abs)/([a-z-]+/\d+)"), "arxiv_{}.pdf"),
        # SSRN: papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567
        (re.compile(r"ssrn\.com/.*abstract_id=(\d+)"), "ssrn_{}.pdf"),
        # NBER: nber.org/papers/w29000
        (re.compile(r"nber\.org/papers/([wW]?\d+)"), "nber_{}.pdf"),
        # DOI-based URLs
        (re.compile(r"doi\.org/(10\.\d{4,9}/[^\s/]+)"), "doi_{}.pdf"),
    ]

    def _filename_from_url(self, url: str) -> str:
        """Extract filename from URL.

        Tries to extract meaningful paper IDs from academic URLs before
        falling back to generic names.

        Args:
            url: URL to extract filename from.

        Returns:
            Filename string.
        """
        parsed = urlparse(url)
        # URL-decode the path to handle encoded characters
        decoded_path = unquote(parsed.path)
        full_url = unquote(url)

        # Try to extract paper ID from URL patterns
        for pattern, template in self._PAPER_ID_PATTERNS:
            match = pattern.search(full_url)
            if match:
                paper_id = match.group(1)
                # Sanitize the paper ID for safe filename
                safe_id = _sanitize_name(paper_id.replace("/", "_"))
                return template.format(safe_id)

        # Use os.path.basename to safely extract just the filename
        basename = os.path.basename(decoded_path)

        if basename.lower().endswith(".pdf"):
            # Use the filename from URL, but sanitize it
            name = os.path.splitext(basename)[0]
            safe_name = _sanitize_name(name)
            return f"{safe_name}.pdf"

        # Fallback: use domain (sanitized)
        domain = _sanitize_name(parsed.netloc.replace(".", "_"))
        return f"{domain}_download.pdf"
