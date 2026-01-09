"""Book processing: chapter detection.

DEPRECATED: This module is superseded by papercutter.ingest.splitter
for the new Factory pipeline. Kept for backwards compatibility with
legacy CLI commands.
"""

from papercutter.legacy.books.splitter import Chapter, ChapterSplitter

__all__ = ["Chapter", "ChapterSplitter"]
