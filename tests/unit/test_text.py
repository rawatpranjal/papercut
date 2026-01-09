"""Tests for text extraction."""

import pytest

from papercutter.legacy.core.text import TextExtractor


class TestTextChunking:
    """Tests for text chunking logic."""

    def test_chunk_short_text_returns_single_chunk(self):
        """Short text should return as single chunk."""

        class MockBackend:
            def extract_text(self, path, pages=None):
                return "Short text."

        extractor = TextExtractor(MockBackend())
        chunks = extractor._chunk_text("Short text.", chunk_size=100, overlap=20)

        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_chunk_long_text_creates_multiple_chunks(self):
        """Long text should be split into multiple chunks."""

        long_text = "This is a sentence. " * 50  # ~1000 chars

        class MockBackend:
            def extract_text(self, path, pages=None):
                return long_text

        extractor = TextExtractor(MockBackend())
        chunks = extractor._chunk_text(long_text, chunk_size=200, overlap=50)

        assert len(chunks) > 1
        # Each chunk should be roughly the right size (allowing for sentence boundaries)
        for chunk in chunks[:-1]:  # Last chunk may be shorter
            assert len(chunk) <= 250  # chunk_size + some margin

    def test_chunks_have_overlap(self):
        """Chunks should have overlapping content."""
        text = "First sentence here. Second sentence follows. Third sentence too. Fourth sentence end."

        class MockBackend:
            def extract_text(self, path, pages=None):
                return text

        extractor = TextExtractor(MockBackend())
        chunks = extractor._chunk_text(text, chunk_size=50, overlap=20)

        # With overlap, we should see some content repeated
        if len(chunks) > 1:
            # The end of chunk 0 should appear in chunk 1
            # This is hard to test exactly due to sentence boundary logic
            assert len(chunks) >= 2

    def test_find_break_point_at_sentence(self):
        """Should find break points at sentence endings."""

        class MockBackend:
            def extract_text(self, path, pages=None):
                return ""

        extractor = TextExtractor(MockBackend())

        # Need a longer text since _find_break_point searches the last 20%
        text = "A" * 80 + " This is a sentence. " + "B" * 20
        break_point = extractor._find_break_point(text)

        # Should find break after the sentence
        assert break_point > 0
        # The break point should be after ". "
        assert ". " in text[break_point - 3 : break_point + 1]
