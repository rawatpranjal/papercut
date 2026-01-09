"""File hashing utilities for Papercutter Factory.

Provides content-based hashing for PDF files to generate unique IDs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def file_hash(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Generate a hash for a file based on content and metadata.

    Uses SHA256 of the first chunk + file size for deterministic hashing.
    This provides fast hashing while still detecting changes.

    Note: Unlike MD5, SHA256 provides better collision resistance
    and is more suitable for content-addressable storage.

    Args:
        path: Path to the file.
        chunk_size: Bytes to read for hashing (default 1MB).

    Returns:
        Hex string hash (12 characters for brevity).
    """
    path = Path(path)
    stat = path.stat()

    hasher = hashlib.sha256()

    # Hash first chunk of content
    with open(path, "rb") as f:
        data = f.read(chunk_size)
        hasher.update(data)

    # Include file size for additional uniqueness
    hasher.update(str(stat.st_size).encode())

    # Return truncated hash (12 chars is ~48 bits = enough for uniqueness)
    return hasher.hexdigest()[:12]


def content_hash(data: bytes) -> str:
    """Generate a hash for arbitrary byte content.

    Args:
        data: Byte content to hash.

    Returns:
        Hex string hash (12 characters).
    """
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()[:12]


def string_hash(text: str) -> str:
    """Generate a hash for string content.

    Args:
        text: String content to hash.

    Returns:
        Hex string hash (12 characters).
    """
    return content_hash(text.encode("utf-8"))


# Alias for backwards compatibility
compute_file_hash = file_hash
