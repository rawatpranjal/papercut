"""Reference resolution - extract identifiers from references."""

import re
from dataclasses import dataclass
from typing import Optional

from papercutter.core.references import Reference
from papercutter.fetchers.registry import FetcherRegistry, ResolvedIdentifier


@dataclass
class ResolvedReference:
    """A reference with resolution status."""

    reference: Reference  # Original reference
    resolved_id: Optional[str] = None  # Resolved identifier (DOI, arXiv ID, URL)
    source_type: Optional[str] = None  # "arxiv", "doi", "url", None
    status: str = "unresolved"  # "resolved", "unresolved", "ambiguous"

    @property
    def is_resolved(self) -> bool:
        """Check if reference was resolved."""
        return self.status == "resolved" and self.resolved_id is not None


class ReferenceResolver:
    """Resolve references to downloadable identifiers.

    Extracts arXiv IDs, DOIs, and URLs from reference text
    and checks if they can be fetched.
    """

    # arXiv ID patterns
    ARXIV_PATTERNS = [
        # Explicit arXiv prefix
        re.compile(r"arXiv[:\s]*(\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE),
        # URL form
        re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE),
        # Old-style arXiv IDs (e.g., hep-th/9901001)
        re.compile(r"arXiv[:\s]*([a-z-]+/\d{7})", re.IGNORECASE),
    ]

    # DOI pattern - more strict to avoid false positives
    DOI_PATTERN = re.compile(
        r"(?:doi[:\s]*)?(?:https?://doi\.org/)?(10\.\d{4,9}/[^\s\])<>,;'\"]+)",
        re.IGNORECASE,
    )

    # URL pattern for direct PDF links
    URL_PATTERN = re.compile(
        r"(https?://[^\s<>\"')\]]+\.pdf(?:\?[^\s]*)?)",
        re.IGNORECASE,
    )

    # Generic URL pattern (fallback)
    GENERIC_URL_PATTERN = re.compile(
        r"(https?://[^\s<>\"')\]]+)",
        re.IGNORECASE,
    )

    def __init__(self, registry: Optional[FetcherRegistry] = None):
        """Initialize resolver.

        Args:
            registry: FetcherRegistry for checking if identifiers are fetchable.
                     If None, creates a default registry.
        """
        if registry is None:
            from papercutter.fetchers.registry import get_registry
            registry = get_registry()
        self.registry = registry

    def resolve(self, reference: Reference) -> ResolvedReference:
        """Resolve a single reference.

        Tries to extract identifiers in priority order:
        1. Use existing doi field if present
        2. Extract arXiv ID from raw_text
        3. Use existing url field if PDF link
        4. Extract DOI from raw_text
        5. Extract PDF URL from raw_text

        Args:
            reference: Reference to resolve.

        Returns:
            ResolvedReference with resolution status.
        """
        # 1. Check existing DOI field
        if reference.doi:
            resolved = self.registry.resolve(reference.doi)
            if resolved:
                return ResolvedReference(
                    reference=reference,
                    resolved_id=resolved.identifier,
                    source_type=resolved.source_type,
                    status="resolved",
                )

        # 2. Extract arXiv ID from raw text
        arxiv_id = self._extract_arxiv_id(reference.raw_text)
        if arxiv_id:
            resolved = self.registry.resolve(arxiv_id)
            if resolved:
                return ResolvedReference(
                    reference=reference,
                    resolved_id=resolved.identifier,
                    source_type=resolved.source_type,
                    status="resolved",
                )

        # 3. Check existing URL field if it's a PDF
        if reference.url and ".pdf" in reference.url.lower():
            resolved = self.registry.resolve(reference.url)
            if resolved:
                return ResolvedReference(
                    reference=reference,
                    resolved_id=resolved.identifier,
                    source_type=resolved.source_type,
                    status="resolved",
                )

        # 4. Extract DOI from raw text
        doi = self._extract_doi(reference.raw_text)
        if doi:
            resolved = self.registry.resolve(doi)
            if resolved:
                return ResolvedReference(
                    reference=reference,
                    resolved_id=resolved.identifier,
                    source_type=resolved.source_type,
                    status="resolved",
                )

        # 5. Extract PDF URL from raw text
        url = self._extract_url(reference.raw_text)
        if url:
            resolved = self.registry.resolve(url)
            if resolved:
                return ResolvedReference(
                    reference=reference,
                    resolved_id=resolved.identifier,
                    source_type=resolved.source_type,
                    status="resolved",
                )

        # Nothing found
        return ResolvedReference(
            reference=reference,
            resolved_id=None,
            source_type=None,
            status="unresolved",
        )

    def resolve_all(
        self, references: list[Reference], deduplicate: bool = True
    ) -> list[ResolvedReference]:
        """Resolve all references.

        Args:
            references: List of references to resolve.
            deduplicate: Remove duplicate resolved identifiers.

        Returns:
            List of ResolvedReferences.
        """
        results = []
        seen_ids = set()

        for ref in references:
            resolved = self.resolve(ref)
            if deduplicate and resolved.is_resolved:
                if resolved.resolved_id in seen_ids:
                    continue
                seen_ids.add(resolved.resolved_id)
            results.append(resolved)

        return results

    def _extract_arxiv_id(self, text: str) -> Optional[str]:
        """Extract arXiv ID from text."""
        for pattern in self.ARXIV_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    def _extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text."""
        match = self.DOI_PATTERN.search(text)
        if match:
            doi = match.group(1)
            # Clean up trailing punctuation
            doi = doi.rstrip(".,;:")
            return doi
        return None

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract PDF URL from text."""
        # Try PDF URL first
        match = self.URL_PATTERN.search(text)
        if match:
            return match.group(1)
        return None
