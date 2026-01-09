"""Caching layer for PDF extractions."""

from papercutter.legacy.cache.hash import file_hash
from papercutter.legacy.cache.store import CacheStore, get_cache

__all__ = ["CacheStore", "file_hash", "get_cache"]
