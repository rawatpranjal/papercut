"""SSRN paper fetcher."""

import re
from pathlib import Path

from papercut.exceptions import FetchError, PaperNotFoundError
from papercut.fetchers.base import BaseFetcher, Document
from papercut.utils.http import download_file, get_client


class SSRNFetcher(BaseFetcher):
    """Fetch papers from SSRN."""

    # Pattern to match SSRN IDs
    # Formats: 1234567, ssrn:1234567, SSRN-id1234567
    PATTERN = re.compile(
        r"^(?:ssrn[:\-]?(?:id)?)?(\d{6,8})$",
        re.IGNORECASE,
    )

    # SSRN abstract page
    ABSTRACT_URL = "https://papers.ssrn.com/sol3/papers.cfm"

    # SSRN PDF download URL template
    PDF_URL = "https://papers.ssrn.com/sol3/Delivery.cfm"

    def can_handle(self, identifier: str) -> bool:
        """Check if this fetcher can handle the given identifier."""
        return bool(self.PATTERN.match(identifier.strip()))

    def normalize_id(self, identifier: str) -> str:
        """Normalize SSRN ID to just the number."""
        identifier = identifier.strip()
        match = self.PATTERN.match(identifier)
        if match:
            return match.group(1)
        return identifier

    def fetch(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch paper from SSRN.

        Args:
            identifier: SSRN paper ID.
            output_dir: Directory to save the downloaded PDF.

        Returns:
            Document object with path and metadata.

        Raises:
            PaperNotFoundError: If paper not found on SSRN.
            FetchError: If download fails.
        """
        ssrn_id = self.normalize_id(identifier)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get metadata from abstract page
        metadata = self._get_metadata(ssrn_id)

        # Generate filename
        filename = self._generate_filename(ssrn_id, metadata)

        # Download PDF
        pdf_url = f"{self.PDF_URL}?abstractid={ssrn_id}"

        try:
            with get_client() as client:
                # SSRN requires specific headers
                response = client.get(
                    pdf_url,
                    headers={
                        "Accept": "application/pdf",
                        "Referer": f"{self.ABSTRACT_URL}?abstract_id={ssrn_id}",
                    },
                )

                if response.status_code == 404:
                    raise PaperNotFoundError(
                        f"Paper not found on SSRN: {ssrn_id}",
                    )

                # Check if we got a PDF
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower():
                    raise FetchError(
                        f"SSRN did not return a PDF for {ssrn_id}",
                        details="The paper may require login or may not be publicly available.",
                    )

                response.raise_for_status()

                # Save the PDF
                pdf_path = output_dir / filename
                pdf_path.write_bytes(response.content)

        except Exception as e:
            if isinstance(e, (PaperNotFoundError, FetchError)):
                raise
            raise FetchError(
                f"Failed to download SSRN paper {ssrn_id}",
                details=str(e),
            ) from e

        return Document(
            path=pdf_path,
            title=metadata.get("title"),
            authors=metadata.get("authors", []),
            source_url=f"{self.ABSTRACT_URL}?abstract_id={ssrn_id}",
        )

    def _get_metadata(self, ssrn_id: str) -> dict:
        """Get paper metadata from SSRN.

        Args:
            ssrn_id: SSRN paper ID.

        Returns:
            Metadata dictionary.
        """
        # Basic metadata extraction from abstract page
        url = f"{self.ABSTRACT_URL}?abstract_id={ssrn_id}"
        metadata = {}

        try:
            with get_client() as client:
                response = client.get(url)

                if response.status_code == 404:
                    return metadata

                response.raise_for_status()
                html = response.text

                # Extract title from meta tag or title element
                title_match = re.search(
                    r'<meta\s+name="citation_title"\s+content="([^"]+)"',
                    html,
                    re.IGNORECASE,
                )
                if title_match:
                    metadata["title"] = title_match.group(1)

                # Extract authors from meta tags
                author_matches = re.findall(
                    r'<meta\s+name="citation_author"\s+content="([^"]+)"',
                    html,
                    re.IGNORECASE,
                )
                if author_matches:
                    metadata["authors"] = author_matches

        except Exception:
            pass

        return metadata

    def _generate_filename(self, ssrn_id: str, metadata: dict) -> str:
        """Generate a filename for the paper.

        Args:
            ssrn_id: SSRN paper ID.
            metadata: Paper metadata.

        Returns:
            Filename string.
        """
        authors = metadata.get("authors", [])
        title = metadata.get("title", "")

        if authors:
            first_author = authors[0].split()[-1]
        else:
            first_author = "ssrn"

        if title:
            title_slug = re.sub(r"[^a-z0-9]+", "_", title.lower())[:40]
            return f"{first_author}_{title_slug}.pdf"

        return f"ssrn_{ssrn_id}.pdf"
