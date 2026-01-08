"""Text extraction and chunking logic."""

from pathlib import Path
from typing import Optional

from papercut.extractors.base import Extractor


class TextExtractor:
    """Extract and process text from PDFs."""

    def __init__(self, backend: Extractor):
        """Initialize with an extraction backend.

        Args:
            backend: PDF extraction backend (e.g., PdfPlumberExtractor).
        """
        self.backend = backend

    def extract(self, path: Path, pages: Optional[list[int]] = None) -> str:
        """Extract full text from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.

        Returns:
            Extracted text as a string.
        """
        return self.backend.extract_text(path, pages)

    def extract_chunked(
        self,
        path: Path,
        chunk_size: int = 4000,
        overlap: int = 200,
        pages: Optional[list[int]] = None,
    ) -> list[str]:
        """Extract text as overlapping chunks for LLM processing.

        Uses character-based chunking with sentence boundary awareness.

        Args:
            path: Path to the PDF file.
            chunk_size: Target size of each chunk in characters.
            overlap: Number of characters to overlap between chunks.
            pages: Optional list of 0-indexed page numbers.

        Returns:
            List of text chunks.
        """
        text = self.extract(path, pages)
        if not text:
            return []

        return self._chunk_text(text, chunk_size, overlap)

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
    ) -> list[str]:
        """Split text into overlapping chunks.

        Tries to break at sentence boundaries when possible.

        Args:
            text: Full text to chunk.
            chunk_size: Target size of each chunk.
            overlap: Characters to overlap between chunks.

        Returns:
            List of text chunks.

        Raises:
            ValueError: If chunk_size or overlap are invalid.
        """
        # Validate parameters to prevent infinite loops
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Get the chunk end position
            end = start + chunk_size

            if end >= len(text):
                # Last chunk - take everything remaining
                chunks.append(text[start:].strip())
                break

            # Try to find a good break point (sentence boundary)
            chunk = text[start:end]
            break_point = self._find_break_point(chunk)

            if break_point > 0:
                end = start + break_point
                chunks.append(text[start:end].strip())
            else:
                # No good break point, just use the chunk size
                chunks.append(chunk.strip())

            # Move start position, accounting for overlap
            start = end - overlap
            if start < 0:
                start = 0

        return chunks

    def _find_break_point(self, text: str) -> int:
        """Find a good break point in text (sentence boundary).

        Looks for sentence-ending punctuation followed by space or newline.

        Args:
            text: Text to find break point in.

        Returns:
            Position of break point, or 0 if none found.
        """
        # Look for break points in the last 20% of the chunk
        search_start = int(len(text) * 0.8)
        search_text = text[search_start:]

        # Sentence endings to look for (in order of preference)
        endings = [". ", ".\n", "? ", "?\n", "! ", "!\n", "\n\n"]

        best_pos = 0
        for ending in endings:
            pos = search_text.rfind(ending)
            if pos >= 0:
                # Calculate position relative to full text
                absolute_pos = search_start + pos + len(ending)
                if absolute_pos > best_pos:
                    best_pos = absolute_pos
                break  # Use first ending type found

        return best_pos
