"""arXiv paper fetcher."""

import asyncio
import re
from pathlib import Path

import arxiv

from papercutter.exceptions import FetchError, PaperNotFoundError
from papercutter.legacy.fetchers.base import BaseFetcher, Document


class ArxivFetcher(BaseFetcher):
    """Fetch papers from arXiv."""

    # Pattern to match arXiv IDs
    # Formats: 2301.00001, 2301.00001v2, arxiv:2301.00001, arXiv:2301.00001v2
    PATTERN = re.compile(
        r"^(?:arxiv:)?(\d{4}\.\d{4,5})(v\d+)?$",
        re.IGNORECASE,
    )

    # Old-style arXiv IDs (e.g., hep-th/9901001)
    OLD_PATTERN = re.compile(
        r"^(?:arxiv:)?([a-z-]+/\d{7})$",
        re.IGNORECASE,
    )

    def can_handle(self, identifier: str) -> bool:
        """Check if this fetcher can handle the given identifier."""
        identifier = identifier.strip()
        return bool(self.PATTERN.match(identifier) or self.OLD_PATTERN.match(identifier))

    def normalize_id(self, identifier: str) -> str:
        """Normalize arXiv ID to standard format."""
        identifier = identifier.strip()

        # Remove 'arxiv:' prefix if present
        if identifier.lower().startswith("arxiv:"):
            identifier = identifier[6:]

        return identifier

    def fetch(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch paper from arXiv.

        Args:
            identifier: arXiv paper ID.
            output_dir: Directory to save the downloaded PDF.

        Returns:
            Document object with path and metadata.

        Raises:
            PaperNotFoundError: If paper not found on arXiv.
            FetchError: If download fails.
        """
        arxiv_id = self.normalize_id(identifier)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Search for the paper
            client = arxiv.Client()
            search = arxiv.Search(id_list=[arxiv_id])
            results = list(client.results(search))

            if not results:
                raise PaperNotFoundError(
                    f"Paper not found on arXiv: {arxiv_id}",
                    details="Check that the arXiv ID is correct.",
                )

            paper = results[0]

            # Generate a clean filename
            first_author = paper.authors[0].name.split()[-1] if paper.authors else "unknown"
            year = paper.published.year if paper.published else "0000"
            title_slug = self._slugify(paper.title)[:50]
            filename = f"{first_author}_{year}_{title_slug}.pdf"

            # Download the PDF
            pdf_path = output_dir / filename
            paper.download_pdf(dirpath=str(output_dir), filename=filename)

            return Document(
                path=pdf_path,
                title=paper.title,
                authors=[author.name for author in paper.authors],
                abstract=paper.summary,
                arxiv_id=paper.entry_id,
                doi=paper.doi,
                source_url=paper.pdf_url,
            )

        except arxiv.HTTPError as e:
            raise FetchError(
                f"Failed to fetch from arXiv: {arxiv_id}",
                details=str(e),
            ) from e
        except Exception as e:
            if isinstance(e, (PaperNotFoundError, FetchError)):
                raise
            raise FetchError(
                f"Unexpected error fetching {arxiv_id}",
                details=str(e),
            ) from e

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug.

        Args:
            text: Text to slugify.

        Returns:
            Slugified string.
        """
        # Convert to lowercase
        text = text.lower()
        # Replace spaces and non-alphanumeric with underscores
        text = re.sub(r"[^a-z0-9]+", "_", text)
        # Remove leading/trailing underscores
        text = text.strip("_")
        return text

    async def fetch_async(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch paper from arXiv asynchronously.

        The underlying arXiv client is synchronous, so this method
        runs the blocking fetch in a background thread.
        """
        return await asyncio.to_thread(self.fetch, identifier, output_dir, **kwargs)
