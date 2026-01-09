"""SSRN paper fetcher."""

import re
from pathlib import Path
from typing import Any

from papercutter.exceptions import FetchError, PaperNotFoundError
from papercutter.legacy.fetchers.base import BaseFetcher, Document
from papercutter.utils.http import get_async_client, get_client


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
                        f"SSRN paper {ssrn_id} requires login",
                        details=(
                            "This paper is not publicly downloadable. "
                            "Register free at https://papers.ssrn.com or try the direct link: "
                            f"{self.ABSTRACT_URL}?abstract_id={ssrn_id}"
                        ),
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

    async def fetch_async(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch paper from SSRN asynchronously."""
        ssrn_id = self.normalize_id(identifier)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        metadata = await self._get_metadata_async(ssrn_id)
        filename = self._generate_filename(ssrn_id, metadata)
        pdf_url = f"{self.PDF_URL}?abstractid={ssrn_id}"

        try:
            async with get_async_client() as client:
                response = await client.get(
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

                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower():
                    raise FetchError(
                        f"SSRN paper {ssrn_id} requires login",
                        details=(
                            "This paper is not publicly downloadable. "
                            "Register free at https://papers.ssrn.com or try the direct link: "
                            f"{self.ABSTRACT_URL}?abstract_id={ssrn_id}"
                        ),
                    )

                response.raise_for_status()

                pdf_path = output_dir / filename
                with open(pdf_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

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
        metadata: dict[str, Any] = {}

        try:
            with get_client() as client:
                response = client.get(url)

                if response.status_code == 404:
                    return metadata

                response.raise_for_status()
                return self._parse_metadata_html(response.text)

        except Exception:
            pass

        return metadata

    async def _get_metadata_async(self, ssrn_id: str) -> dict:
        """Async metadata fetch from SSRN."""
        url = f"{self.ABSTRACT_URL}?abstract_id={ssrn_id}"

        try:
            async with get_async_client() as client:
                response = await client.get(url)

                if response.status_code == 404:
                    return {}

                response.raise_for_status()
                return self._parse_metadata_html(response.text)
        except Exception:
            return {}

    def _parse_metadata_html(self, html: str) -> dict:
        """Parse SSRN metadata from HTML."""
        metadata: dict[str, Any] = {}

        title_match = re.search(
            r'<meta\s+name="citation_title"\s+content="([^"]+)"',
            html,
            re.IGNORECASE,
        )
        if title_match:
            metadata["title"] = title_match.group(1)

        author_matches = re.findall(
            r'<meta\s+name="citation_author"\s+content="([^"]+)"',
            html,
            re.IGNORECASE,
        )
        if author_matches:
            metadata["authors"] = author_matches

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
