"""Security tests for path traversal, API key handling, and other vulnerabilities."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestPathTraversalPrevention:
    """Test path traversal prevention in file downloads."""

    def test_sanitize_filename_removes_path_traversal(self):
        """Test that path traversal sequences are removed from filenames."""
        from papercutter.utils.http import _sanitize_filename

        # Test basic path traversal
        assert _sanitize_filename("../../../etc/passwd") == "passwd"
        assert _sanitize_filename("..\\..\\..\\windows\\system32") == "system32"

        # Test URL-encoded traversal
        assert _sanitize_filename("%2e%2e%2fetc%2fpasswd") == "passwd"

        # Test leading dots
        assert _sanitize_filename("...hidden") == "hidden"
        assert _sanitize_filename("..file.pdf") == "file.pdf"

        # Test dangerous characters
        assert _sanitize_filename("file<>:\"|?*.pdf") == "file_______.pdf"

        # Test empty/invalid names
        assert _sanitize_filename("") == "download"
        assert _sanitize_filename("..") == "download"
        assert _sanitize_filename(".") == "download"

        # Test normal filenames are preserved
        assert _sanitize_filename("paper.pdf") == "paper.pdf"
        assert _sanitize_filename("my-paper_2024.pdf") == "my-paper_2024.pdf"

    def test_sanitize_filename_limits_length(self):
        """Test that overly long filenames are truncated."""
        from papercutter.utils.http import _sanitize_filename

        long_name = "a" * 300 + ".pdf"
        result = _sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".pdf")


class TestURLFetcherSanitization:
    """Test URL fetcher filename sanitization."""

    def test_sanitize_name_removes_traversal(self):
        """Test that user-provided names are sanitized."""
        from papercutter.legacy.fetchers.url import _sanitize_name

        # Test path traversal
        assert _sanitize_name("../../../etc/passwd") == "passwd"

        # Test dangerous characters replaced
        result = _sanitize_name("file<with>special:chars")
        assert "/" not in result
        assert "\\" not in result
        assert ".." not in result

        # Test empty result
        assert _sanitize_name("") == "download"
        assert _sanitize_name("..") == "download"


class TestChunkingInfiniteLoopPrevention:
    """Test infinite loop prevention in text chunking."""

    def test_chunk_text_rejects_invalid_overlap(self):
        """Test that overlap >= chunk_size raises an error."""
        from papercutter.legacy.core.text import TextExtractor
        from unittest.mock import Mock

        backend = Mock()
        backend.extract_text.return_value = "Some text " * 100
        extractor = TextExtractor(backend)

        # overlap >= chunk_size should raise
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            extractor.extract_chunked(Path("test.pdf"), chunk_size=100, overlap=100)

        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            extractor.extract_chunked(Path("test.pdf"), chunk_size=100, overlap=200)

    def test_chunk_text_rejects_invalid_chunk_size(self):
        """Test that chunk_size <= 0 raises an error."""
        from papercutter.legacy.core.text import TextExtractor
        from unittest.mock import Mock

        backend = Mock()
        backend.extract_text.return_value = "Some text"
        extractor = TextExtractor(backend)

        with pytest.raises(ValueError, match="chunk_size must be a positive integer"):
            extractor.extract_chunked(Path("test.pdf"), chunk_size=0)

        with pytest.raises(ValueError, match="chunk_size must be a positive integer"):
            extractor.extract_chunked(Path("test.pdf"), chunk_size=-10)


class TestPageValidationWarnings:
    """Test that invalid page indices generate warnings."""

    def test_invalid_pages_generate_warning(self):
        """Test that out-of-range pages generate warnings."""
        from papercutter.extractors.pdfplumber import _validate_page_indices

        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _validate_page_indices([0, 1, 2, 100, -1], total_pages=3)

            # Should only return valid pages
            assert result == [0, 1, 2]

            # Should have raised a warning
            assert len(w) == 1
            assert "invalid page indices" in str(w[0].message).lower()
            assert "100" in str(w[0].message)
            assert "-1" in str(w[0].message)


class TestBibTeXSanitization:
    """Test BibTeX output sanitization."""

    def test_bibtex_removes_newlines(self):
        """Test that newlines are removed from BibTeX fields."""
        from papercutter.legacy.core.references import Reference

        ref = Reference(
            raw_text="Test reference",
            title="This is a\nmulti-line\ntitle",
            authors=["John\nSmith"],
            year=2024,
        )

        bibtex = ref.to_bibtex()

        # No raw newlines in field values (only the structural newlines between fields)
        lines = bibtex.split("\n")
        for line in lines:
            if "title =" in line or "author =" in line:
                # The field value should be on a single line
                assert line.count("{") == line.count("}")

    def test_bibtex_escapes_special_chars(self):
        """Test that special BibTeX characters are escaped."""
        from papercutter.legacy.core.references import Reference

        ref = Reference(
            raw_text="Test reference",
            title="100% Accuracy & Performance",
            authors=["John Smith"],
            year=2024,
        )

        bibtex = ref.to_bibtex()

        # % and & should be escaped
        assert "\\%" in bibtex
        assert "\\&" in bibtex


class TestAuthorDeduplication:
    """Test that duplicate authors are removed."""

    def test_duplicate_authors_removed(self):
        """Test that duplicate author names are deduplicated."""
        from papercutter.legacy.core.references import ReferenceExtractor
        from unittest.mock import Mock

        backend = Mock()
        extractor = ReferenceExtractor(backend)

        # Simulate text with duplicate authors due to parsing artifacts
        raw_text = "Smith, J., Smith, J. (2020) Some paper title."

        ref = extractor._parse_reference(raw_text)

        # Should not have duplicate authors
        author_names_lower = [a.lower() for a in ref.authors]
        assert len(author_names_lower) == len(set(author_names_lower))

    def test_and_not_included_as_author(self):
        """Test that 'and' is not included as an author name."""
        from papercutter.legacy.core.references import ReferenceExtractor
        from unittest.mock import Mock

        backend = Mock()
        extractor = ReferenceExtractor(backend)

        # Text that might produce "and" as an author
        raw_text = "Smith, J. and and Jones, K. (2020) Paper title."

        ref = extractor._parse_reference(raw_text)

        # "and" should not be in the author list
        for author in ref.authors:
            assert author.lower() != "and"
