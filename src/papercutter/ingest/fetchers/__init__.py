"""Paper fetchers for various academic sources.

Moved from papercutter.fetchers to papercutter.ingest.fetchers
as part of the Papercutter Factory refactor.
"""

from papercutter.ingest.fetchers.base import BaseFetcher, Document
from papercutter.ingest.fetchers.registry import (
    FetcherRegistry,
    ResolvedIdentifier,
    get_registry,
)

__all__ = [
    "BaseFetcher",
    "Document",
    "FetcherRegistry",
    "ResolvedIdentifier",
    "get_registry",
]
