"""Fetcher registry for automatic identifier dispatch."""

from dataclasses import dataclass
from pathlib import Path

from papercutter.fetchers.base import BaseFetcher, Document


@dataclass
class ResolvedIdentifier:
    """Result of identifier resolution."""

    identifier: str  # Normalized identifier
    fetcher: BaseFetcher  # Fetcher that can handle it
    source_type: str  # "arxiv", "doi", "url", etc.


class FetcherRegistry:
    """Registry for paper fetchers with automatic dispatch.

    Fetchers are tried in priority order (lower = tried first).
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._fetchers: list[tuple[BaseFetcher, int, str]] = []  # (fetcher, priority, name)

    def register(self, fetcher: BaseFetcher, priority: int = 50, name: str = "") -> None:
        """Register a fetcher with priority.

        Args:
            fetcher: Fetcher instance to register.
            priority: Priority (lower = tried first). Default 50.
            name: Name/type for this fetcher (e.g., "arxiv", "doi").
        """
        if not name:
            name = fetcher.__class__.__name__.lower().replace("fetcher", "")
        self._fetchers.append((fetcher, priority, name))
        # Keep sorted by priority
        self._fetchers.sort(key=lambda x: x[1])

    def resolve(self, identifier: str) -> ResolvedIdentifier | None:
        """Find the best fetcher for an identifier.

        Args:
            identifier: Identifier to resolve (DOI, arXiv ID, URL, etc.)

        Returns:
            ResolvedIdentifier if a fetcher can handle it, None otherwise.
        """
        for fetcher, _, name in self._fetchers:
            if fetcher.can_handle(identifier):
                normalized = fetcher.normalize_id(identifier)
                return ResolvedIdentifier(
                    identifier=normalized,
                    fetcher=fetcher,
                    source_type=name,
                )
        return None

    def resolve_all(self, identifier: str) -> list[ResolvedIdentifier]:
        """Find all fetchers that can handle an identifier.

        Useful for fallback when primary fetcher fails.

        Args:
            identifier: Identifier to resolve.

        Returns:
            List of ResolvedIdentifiers, ordered by priority.
        """
        results = []
        for fetcher, _, name in self._fetchers:
            if fetcher.can_handle(identifier):
                normalized = fetcher.normalize_id(identifier)
                results.append(
                    ResolvedIdentifier(
                        identifier=normalized,
                        fetcher=fetcher,
                        source_type=name,
                    )
                )
        return results

    def fetch(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch using the best available fetcher.

        Args:
            identifier: Identifier to fetch.
            output_dir: Directory to save the PDF.
            **kwargs: Additional options passed to fetcher.

        Returns:
            Document from the fetcher.

        Raises:
            ValueError: If no fetcher can handle the identifier.
        """
        resolved = self.resolve(identifier)
        if not resolved:
            raise ValueError(f"No fetcher can handle identifier: {identifier}")
        return resolved.fetcher.fetch(resolved.identifier, output_dir, **kwargs)

    async def fetch_async(self, identifier: str, output_dir: Path, **kwargs) -> Document:
        """Fetch using the best available fetcher asynchronously."""
        resolved = self.resolve(identifier)
        if not resolved:
            raise ValueError(f"No fetcher can handle identifier: {identifier}")
        return await resolved.fetcher.fetch_async(resolved.identifier, output_dir, **kwargs)

    @property
    def fetchers(self) -> list[tuple[str, int]]:
        """Get list of registered fetchers with their priorities."""
        return [(name, priority) for _, priority, name in self._fetchers]


def get_registry() -> FetcherRegistry:
    """Get a global fetcher registry with all fetchers registered.

    Returns:
        FetcherRegistry with standard fetchers.
    """
    from papercutter.fetchers.arxiv import ArxivFetcher
    from papercutter.fetchers.doi import DOIFetcher
    from papercutter.fetchers.nber import NBERFetcher
    from papercutter.fetchers.ssrn import SSRNFetcher
    from papercutter.fetchers.url import URLFetcher

    registry = FetcherRegistry()

    # Register fetchers in priority order (lower = tried first)
    registry.register(ArxivFetcher(), priority=10, name="arxiv")
    registry.register(DOIFetcher(), priority=20, name="doi")
    registry.register(SSRNFetcher(), priority=30, name="ssrn")
    registry.register(NBERFetcher(), priority=30, name="nber")
    registry.register(URLFetcher(), priority=100, name="url")  # Fallback

    return registry
