"""NBER working paper fetcher."""

import re
from pathlib import Path

from papercut.exceptions import FetchError, PaperNotFoundError
from papercut.fetchers.base import BaseFetcher, Document
from papercut.utils.http import download_file, get_client


class NBERFetcher(BaseFetcher):
    """Fetch working papers from NBER."""

    # Pattern to match NBER IDs
    # Formats: w29000, W29000, nber:w29000, 29000
    PATTERN = re.compile(
        r"^(?:nber:)?[wW]?(\d{4,6})$",
        re.IGNORECASE,
    )

    # NBER paper page
    PAPER_URL = "https://www.nber.org/papers/w{paper_id}"

    # NBER PDF URL template
    PDF_URL = "https://www.nber.org/system/files/working_papers/w{paper_id}/w{paper_id}.pdf"

    def can_handle(self, identifier: str) -> bool:
        """Check if this fetcher can handle the given identifier."""
        return bool(self.PATTERN.match(identifier.strip()))

    def normalize_id(self, identifier: str) -> str:
        """Normalize NBER ID to just the number."""
        identifier = identifier.strip()
        match = self.PATTERN.match(identifier)
        if match:
            return match.group(1)
        return identifier

    def fetch(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch working paper from NBER.

        Args:
            identifier: NBER working paper ID.
            output_dir: Directory to save the downloaded PDF.

        Returns:
            Document object with path and metadata.

        Raises:
            PaperNotFoundError: If paper not found on NBER.
            FetchError: If download fails.
        """
        paper_id = self.normalize_id(identifier)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get metadata from paper page
        metadata = self._get_metadata(paper_id)

        # Generate filename
        filename = self._generate_filename(paper_id, metadata)

        # Download PDF
        pdf_url = self.PDF_URL.format(paper_id=paper_id)

        try:
            pdf_path = download_file(pdf_url, output_dir, filename)
        except Exception as e:
            # Check if it's a 404
            if "404" in str(e):
                raise PaperNotFoundError(
                    f"NBER working paper not found: w{paper_id}",
                    details="Check that the paper ID is correct.",
                ) from e
            raise FetchError(
                f"Failed to download NBER paper w{paper_id}",
                details=str(e),
            ) from e

        return Document(
            path=pdf_path,
            title=metadata.get("title"),
            authors=metadata.get("authors", []),
            abstract=metadata.get("abstract"),
            source_url=self.PAPER_URL.format(paper_id=paper_id),
        )

    def _get_metadata(self, paper_id: str) -> dict:
        """Get paper metadata from NBER.

        Args:
            paper_id: NBER paper ID (number only).

        Returns:
            Metadata dictionary.
        """
        url = self.PAPER_URL.format(paper_id=paper_id)
        metadata = {}

        try:
            with get_client() as client:
                response = client.get(url)

                if response.status_code == 404:
                    return metadata

                response.raise_for_status()
                html = response.text

                # Extract title from meta tag
                title_match = re.search(
                    r'<meta\s+property="og:title"\s+content="([^"]+)"',
                    html,
                    re.IGNORECASE,
                )
                if title_match:
                    metadata["title"] = title_match.group(1)

                # Extract authors from citation_author meta tags
                author_matches = re.findall(
                    r'<meta\s+name="citation_author"\s+content="([^"]+)"',
                    html,
                    re.IGNORECASE,
                )
                if author_matches:
                    metadata["authors"] = author_matches

                # Extract abstract from meta description
                abstract_match = re.search(
                    r'<meta\s+name="description"\s+content="([^"]+)"',
                    html,
                    re.IGNORECASE,
                )
                if abstract_match:
                    metadata["abstract"] = abstract_match.group(1)

        except Exception:
            pass

        return metadata

    def _generate_filename(self, paper_id: str, metadata: dict) -> str:
        """Generate a filename for the paper.

        Args:
            paper_id: NBER paper ID.
            metadata: Paper metadata.

        Returns:
            Filename string.
        """
        authors = metadata.get("authors", [])
        title = metadata.get("title", "")

        if authors:
            first_author = authors[0].split()[-1]
        else:
            first_author = "nber"

        if title:
            title_slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:40]
            return f"{first_author}_{title_slug}.pdf"

        return f"nber_w{paper_id}.pdf"
