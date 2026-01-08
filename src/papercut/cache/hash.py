"""File hashing for cache keys."""

import hashlib
from pathlib import Path


def file_hash(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Generate a hash for a file based on content and metadata.

    Uses MD5 of the first chunk + file size + modification time.
    This provides fast hashing while still detecting changes.

    Args:
        path: Path to the file.
        chunk_size: Bytes to read for hashing (default 1MB).

    Returns:
        Hex string hash (12 characters).
    """
    path = Path(path)
    stat = path.stat()

    hasher = hashlib.md5()

    # Hash first chunk of content
    with open(path, "rb") as f:
        data = f.read(chunk_size)
        hasher.update(data)

    # Include file metadata
    hasher.update(str(stat.st_size).encode())
    hasher.update(str(int(stat.st_mtime)).encode())

    # Return truncated hash (12 chars is enough for uniqueness)
    return hasher.hexdigest()[:12]
