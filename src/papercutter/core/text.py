"""Text extraction and chunking logic."""

import bisect
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from papercutter.extractors.base import Extractor


@dataclass
class ChunkMetadata:
    """Metadata about a text chunk for LLM context."""

    page: int  # Primary page (1-indexed)
    page_end: int | None = None  # End page if chunk spans multiple (1-indexed)
    section: str | None = None  # Section title if detected
    char_start: int = 0  # Start position in full document
    char_end: int = 0  # End position in full document
    figures_referenced: list[str] = field(default_factory=list)
    tables_referenced: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        result: dict[str, Any] = {
            "page": self.page,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }
        if self.page_end and self.page_end != self.page:
            result["page_end"] = self.page_end
        if self.section:
            result["section"] = self.section
        if self.figures_referenced:
            result["figures_referenced"] = self.figures_referenced
        if self.tables_referenced:
            result["tables_referenced"] = self.tables_referenced
        return result


@dataclass
class TextChunk:
    """A text chunk with metadata for LLM processing."""

    id: int
    text: str
    metadata: ChunkMetadata

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata.to_dict(),
        }


class TextExtractor:
    """Extract and process text from PDFs."""

    def __init__(self, backend: Extractor):
        """Initialize with an extraction backend.

        Args:
            backend: PDF extraction backend (e.g., PdfPlumberExtractor).
        """
        self.backend = backend

    def extract(self, path: Path, pages: list[int] | None = None) -> str:
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
        pages: list[int] | None = None,
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

        # Safety: calculate max iterations to prevent infinite loops
        # Even with overlap, we should never need more iterations than text_len / (chunk_size - overlap) + padding
        max_iterations = (len(text) // max(1, chunk_size - overlap)) + 100
        iteration = 0

        while start < len(text):
            iteration += 1
            if iteration > max_iterations:
                raise RuntimeError(
                    f"Text chunking exceeded {max_iterations} iterations - possible infinite loop. "
                    f"text_len={len(text)}, chunk_size={chunk_size}, overlap={overlap}"
                )

            # Get the chunk end position
            end = start + chunk_size

            if end >= len(text):
                # Last chunk - take everything remaining
                # Use rstrip to preserve leading whitespace (paragraph indentation)
                chunks.append(text[start:].rstrip())
                break

            # Try to find a good break point (sentence boundary)
            chunk = text[start:end]
            break_point = self._find_break_point(chunk)

            if break_point > 0:
                end = start + break_point
                # Use rstrip to preserve leading whitespace
                chunks.append(text[start:end].rstrip())
            else:
                # No good break point, just use the chunk size
                chunks.append(chunk.rstrip())

            # Move start position, accounting for overlap
            start = end - overlap
            if start < 0:
                start = 0

        # Filter out empty chunks
        return [c for c in chunks if c]

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

    # Patterns for detecting figure/table references in text
    FIGURE_PATTERNS = [
        re.compile(r"Figure\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
        re.compile(r"Fig\.\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
        re.compile(r"Figs?\.\s*(\d+(?:\s*[-–]\s*\d+)?)", re.IGNORECASE),
    ]

    TABLE_PATTERNS = [
        re.compile(r"Table\s+(\d+(?:\.\d+)?)", re.IGNORECASE),
        re.compile(r"Tab\.\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    ]

    def _extract_references(self, text: str) -> tuple[list[str], list[str]]:
        """Extract figure and table references from text.

        Args:
            text: Text to search for references.

        Returns:
            Tuple of (figure_refs, table_refs) with matched strings.
        """
        figure_refs = set()
        for pattern in self.FIGURE_PATTERNS:
            for match in pattern.finditer(text):
                figure_refs.add(match.group(0))

        table_refs = set()
        for pattern in self.TABLE_PATTERNS:
            for match in pattern.finditer(text):
                table_refs.add(match.group(0))

        return (sorted(figure_refs), sorted(table_refs))

    def extract_chunked_with_metadata(
        self,
        path: Path,
        chunk_size: int = 4000,
        overlap: int = 200,
        pages: list[int] | None = None,
        sections: list | None = None,
        detect_references: bool = True,
    ) -> list[TextChunk]:
        """Extract text as chunks with rich metadata for LLM processing.

        Args:
            path: Path to the PDF file.
            chunk_size: Target size of each chunk in characters.
            overlap: Number of characters to overlap between chunks.
            pages: Optional list of 0-indexed page numbers.
            sections: Optional section info from DocumentIndexer.
            detect_references: Whether to scan for figure/table references.

        Returns:
            List of TextChunk objects with metadata.
        """
        # Validate parameters
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        # Extract text by page to preserve page boundaries
        page_texts = self.backend.extract_text_by_page(path, pages)
        if not page_texts:
            return []

        # Build full text and page offset lookup
        full_text_parts = []
        page_offsets = []  # (char_offset, page_num_0indexed)
        current_offset = 0

        for page_num, page_text in page_texts:
            page_offsets.append((current_offset, page_num))
            full_text_parts.append(page_text)
            current_offset += len(page_text) + 2  # +2 for "\n\n" joiner

        full_text = "\n\n".join(full_text_parts)

        if len(full_text) <= chunk_size:
            # Single chunk for small documents
            fig_refs: list[str] = []
            table_refs: list[str] = []
            if detect_references:
                fig_refs, table_refs = self._extract_references(full_text)

            first_page = page_texts[0][0] + 1  # 1-indexed
            last_page = page_texts[-1][0] + 1
            section_name = self._get_section_for_position(0, sections) if sections else None

            return [
                TextChunk(
                    id=0,
                    text=full_text,
                    metadata=ChunkMetadata(
                        page=first_page,
                        page_end=last_page if last_page != first_page else None,
                        section=section_name,
                        char_start=0,
                        char_end=len(full_text),
                        figures_referenced=fig_refs,
                        tables_referenced=table_refs,
                    ),
                )
            ]

        # Build section map if sections provided
        section_map = self._build_section_map(page_offsets, sections) if sections else []

        # Chunk the text
        chunks = []
        chunk_id = 0
        start = 0

        # Safety: calculate max iterations to prevent infinite loops
        max_iterations = (len(full_text) // max(1, chunk_size - overlap)) + 100
        iteration = 0

        while start < len(full_text):
            iteration += 1
            if iteration > max_iterations:
                raise RuntimeError(
                    f"Text chunking exceeded {max_iterations} iterations - possible infinite loop. "
                    f"text_len={len(full_text)}, chunk_size={chunk_size}, overlap={overlap}"
                )

            end = start + chunk_size

            if end >= len(full_text):
                # Last chunk
                chunk_text = full_text[start:].rstrip()
                end = len(full_text)
            else:
                # Try to find a good break point
                temp_chunk = full_text[start:end]
                break_point = self._find_break_point(temp_chunk)

                if break_point > 0:
                    end = start + break_point
                    chunk_text = full_text[start:end].rstrip()
                else:
                    chunk_text = temp_chunk.rstrip()

            if not chunk_text:
                start = end - overlap
                if start <= 0:
                    break
                continue

            # Determine page range for this chunk
            start_page = self._get_page_for_position(start, page_offsets) + 1  # 1-indexed
            end_page = self._get_page_for_position(end - 1, page_offsets) + 1

            # Get section
            section_name = self._get_section_for_position(start, section_map) if section_map else None

            # Extract references if enabled
            fig_refs, table_refs = ([], [])
            if detect_references:
                fig_refs, table_refs = self._extract_references(chunk_text)

            chunks.append(
                TextChunk(
                    id=chunk_id,
                    text=chunk_text,
                    metadata=ChunkMetadata(
                        page=start_page,
                        page_end=end_page if end_page != start_page else None,
                        section=section_name,
                        char_start=start,
                        char_end=start + len(chunk_text),
                        figures_referenced=fig_refs,
                        tables_referenced=table_refs,
                    ),
                )
            )

            chunk_id += 1
            start = end - overlap
            if start < 0:
                start = 0

            # Handle end of text
            if end >= len(full_text):
                break

        return chunks

    def _get_page_for_position(
        self, char_pos: int, page_offsets: list[tuple[int, int]]
    ) -> int:
        """Get 0-indexed page number for a character position."""
        offsets = [o[0] for o in page_offsets]
        idx = bisect.bisect_right(offsets, char_pos) - 1
        if idx < 0:
            return page_offsets[0][1]
        return page_offsets[idx][1]

    def _build_section_map(
        self, page_offsets: list[tuple[int, int]], sections: list
    ) -> list[tuple[int, str]]:
        """Build sorted mapping from character position to section title.

        Returns sorted list of (char_offset, section_title) tuples for
        efficient binary search lookup.
        """
        if not sections:
            return []

        section_list = []
        for section in sections:
            # sections have pages as 1-indexed tuples
            section_start_page = section.pages[0] - 1  # Convert to 0-indexed

            # Find character offset for this page
            for offset, page_num in page_offsets:
                if page_num == section_start_page:
                    section_list.append((offset, section.title))
                    break

        # Sort by offset for binary search
        section_list.sort(key=lambda x: x[0])
        return section_list

    def _get_section_for_position(
        self, char_pos: int, section_map: list[tuple[int, str]]
    ) -> str | None:
        """Get section title for a character position using binary search."""
        if not section_map:
            return None
        # Extract offsets for binary search
        offsets = [s[0] for s in section_map]
        idx = bisect.bisect_right(offsets, char_pos) - 1
        if idx < 0:
            return None
        return section_map[idx][1]
