"""DOI resolver and fetcher."""

import re
from pathlib import Path
from typing import Optional

from papercut.exceptions import FetchError, PaperNotFoundError
from papercut.fetchers.base import BaseFetcher, Document
from papercut.utils.http import download_file, get_client


class DOIFetcher(BaseFetcher):
    """Resolve DOIs and fetch papers."""

    # Pattern to match DOIs
    # Format: 10.xxxx/... (DOI prefix starts with 10.)
    PATTERN = re.compile(
        r"^(?:doi:|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,}/[^\s]+)$",
        re.IGNORECASE,
    )

    # CrossRef API endpoint
    CROSSREF_API = "https://api.crossref.org/works"

    # DOI resolver
    DOI_RESOLVER = "https://doi.org"

    def can_handle(self, identifier: str) -> bool:
        """Check if this fetcher can handle the given identifier."""
        return bool(self.PATTERN.match(identifier.strip()))

    def normalize_id(self, identifier: str) -> str:
        """Normalize DOI to standard format (just the DOI, no prefix)."""
        identifier = identifier.strip()
        match = self.PATTERN.match(identifier)
        if match:
            return match.group(1)
        return identifier

    def fetch(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Resolve DOI and attempt to fetch paper.

        Args:
            identifier: DOI identifier.
            output_dir: Directory to save the downloaded PDF.

        Returns:
            Document object with path and metadata.

        Raises:
            PaperNotFoundError: If DOI cannot be resolved.
            FetchError: If download fails.
        """
        doi = self.normalize_id(identifier)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get metadata from CrossRef
        metadata = self._get_crossref_metadata(doi)

        # Try to find PDF URL
        pdf_url = self._find_pdf_url(doi, metadata)

        if not pdf_url:
            raise FetchError(
                f"Could not find PDF for DOI: {doi}",
                details="The paper may require institutional access or purchase.",
            )

        # Generate filename
        filename = self._generate_filename(doi, metadata)

        # Download the PDF
        pdf_path = download_file(pdf_url, output_dir, filename)

        return Document(
            path=pdf_path,
            title=metadata.get("title"),
            authors=metadata.get("authors", []),
            doi=doi,
            source_url=pdf_url,
        )

    def _get_crossref_metadata(self, doi: str) -> dict:
        """Fetch metadata from CrossRef API.

        Args:
            doi: DOI to look up.

        Returns:
            Metadata dictionary.

        Raises:
            PaperNotFoundError: If DOI not found.
        """
        url = f"{self.CROSSREF_API}/{doi}"

        with get_client() as client:
            response = client.get(url)

            if response.status_code == 404:
                raise PaperNotFoundError(
                    f"DOI not found: {doi}",
                    details="Check that the DOI is correct.",
                )

            response.raise_for_status()
            data = response.json()

        work = data.get("message", {})

        # Extract relevant fields
        metadata = {}

        # Title
        titles = work.get("title", [])
        if titles:
            metadata["title"] = titles[0]

        # Authors
        authors = work.get("author", [])
        metadata["authors"] = [
            f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors
        ]

        # Journal
        containers = work.get("container-title", [])
        if containers:
            metadata["journal"] = containers[0]

        # Links
        metadata["links"] = work.get("link", [])

        return metadata

    def _find_pdf_url(self, doi: str, metadata: dict) -> Optional[str]:
        """Try to find a PDF URL for the DOI.

        Args:
            doi: DOI of the paper.
            metadata: CrossRef metadata.

        Returns:
            PDF URL if found, None otherwise.
        """
        # Check CrossRef links for PDF
        for link in metadata.get("links", []):
            if link.get("content-type") == "application/pdf":
                return link.get("URL")

        # Try Unpaywall API (free legal copies)
        unpaywall_url = self._check_unpaywall(doi)
        if unpaywall_url:
            return unpaywall_url

        # Try direct DOI resolution with PDF headers
        # Some publishers redirect to PDF directly
        try:
            with get_client() as client:
                response = client.head(
                    f"{self.DOI_RESOLVER}/{doi}",
                    headers={"Accept": "application/pdf"},
                )
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type.lower():
                    return str(response.url)
        except Exception:
            pass

        return None

    def _check_unpaywall(self, doi: str) -> Optional[str]:
        """Check Unpaywall API for free PDF.

        Args:
            doi: DOI to check.

        Returns:
            PDF URL if available, None otherwise.
        """
        # Unpaywall requires an email parameter
        url = f"https://api.unpaywall.org/v2/{doi}"
        params = {"email": "papercut@example.com"}

        try:
            with get_client() as client:
                response = client.get(url, params=params)
                if response.status_code != 200:
                    return None

                data = response.json()
                best_oa = data.get("best_oa_location", {})
                if best_oa:
                    return best_oa.get("url_for_pdf") or best_oa.get("url")
        except Exception:
            pass

        return None

    def _generate_filename(self, doi: str, metadata: dict) -> str:
        """Generate a filename for the paper.

        Args:
            doi: Paper DOI.
            metadata: Paper metadata.

        Returns:
            Filename string.
        """
        # Try to use author and title
        authors = metadata.get("authors", [])
        title = metadata.get("title", "")

        if authors:
            first_author = authors[0].split()[-1]  # Last name
        else:
            first_author = "unknown"

        if title:
            # Slugify title
            title_slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:50]
        else:
            # Use DOI as fallback
            title_slug = re.sub(r"[^a-z0-9]+", "_", doi.lower())[:50]

        return f"{first_author}_{title_slug}.pdf"
