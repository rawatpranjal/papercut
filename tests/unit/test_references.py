"""Tests for reference extraction."""

import pytest

from papercutter.core.references import Reference, ReferenceExtractor


class TestReference:
    """Tests for Reference dataclass."""

    def test_to_bibtex_basic(self):
        """Should generate valid BibTeX entry."""
        ref = Reference(
            raw_text="Smith, J. (2020). A great paper. Journal of Testing, 1, 1-10.",
            title="A great paper",
            authors=["Smith, J."],
            year=2020,
            journal="Journal of Testing",
            pages="1-10",
        )

        bibtex = ref.to_bibtex()

        assert "@article{smith2020great," in bibtex
        assert "author = {Smith, J.}" in bibtex
        assert "title = {A great paper}" in bibtex
        assert "year = {2020}" in bibtex
        assert "journal = {Journal of Testing}" in bibtex
        assert "pages = {1-10}" in bibtex

    def test_to_bibtex_misc_type_without_journal(self):
        """Should use @misc type when no journal."""
        ref = Reference(
            raw_text="Working paper",
            title="Some Working Paper",
            authors=["Doe, J."],
            year=2021,
        )

        bibtex = ref.to_bibtex()

        assert "@misc{" in bibtex

    def test_to_bibtex_with_doi(self):
        """Should include DOI in BibTeX."""
        ref = Reference(
            raw_text="Paper with DOI",
            doi="10.1234/example",
        )

        bibtex = ref.to_bibtex()

        assert "doi = {10.1234/example}" in bibtex

    def test_to_dict(self):
        """Should convert to dictionary."""
        ref = Reference(
            raw_text="Test reference",
            title="Test Title",
            authors=["Author One", "Author Two"],
            year=2022,
        )

        d = ref.to_dict()

        assert d["title"] == "Test Title"
        assert d["authors"] == ["Author One", "Author Two"]
        assert d["year"] == 2022

    def test_generate_key_from_author(self):
        """Should generate key from first author's last name and title."""
        ref = Reference(
            raw_text="Test",
            authors=["van der Berg, Jan"],
            year=2020,
            title="Some Paper Title",
        )

        key = ref._generate_key()

        assert key == "vanderberg2020some"

    def test_generate_key_unknown_author(self):
        """Should use 'unknown' when no authors."""
        ref = Reference(
            raw_text="Test",
            year=2020,
        )

        key = ref._generate_key()

        assert key == "unknown2020"

    def test_generate_key_attention_paper(self):
        """Should generate proper key like vaswani2017attention."""
        ref = Reference(
            raw_text="Test",
            authors=["Vaswani, Ashish"],
            year=2017,
            title="Attention Is All You Need",
        )

        key = ref._generate_key()

        assert key == "vaswani2017attention"

    def test_generate_key_skips_common_words(self):
        """Should skip common words in title."""
        ref = Reference(
            raw_text="Test",
            authors=["Smith, John"],
            year=2020,
            title="The Theory of Everything",
        )

        key = ref._generate_key()

        assert key == "smith2020theory"

    def test_generate_key_simple_name(self):
        """Should handle simple First Last format."""
        ref = Reference(
            raw_text="Test",
            authors=["John Smith"],
            year=2021,
            title="Machine Learning Basics",
        )

        key = ref._generate_key()

        assert key == "smith2021machine"

    def test_generate_key_hyphenated_name(self):
        """Should handle hyphenated last names."""
        ref = Reference(
            raw_text="Test",
            authors=["Smith-Jones, Mary"],
            year=2022,
            title="Testing Hyphenated Names",
        )

        key = ref._generate_key()

        assert key == "smithjones2022testing"


class TestReferenceExtractor:
    """Tests for ReferenceExtractor."""

    def test_find_references_section(self):
        """Should find references section in text."""

        class MockBackend:
            def extract_text(self, path, pages=None):
                return """
                Introduction
                This is the intro.

                References

                Smith, J. (2020). Paper one.
                Doe, A. (2021). Paper two.
                """

        extractor = ReferenceExtractor(MockBackend())
        text = MockBackend().extract_text(None)
        refs_section = extractor._find_references_section(text)

        assert refs_section is not None
        assert "Smith, J. (2020)" in refs_section

    def test_find_bibliography_section(self):
        """Should also find 'Bibliography' header."""

        class MockBackend:
            def extract_text(self, path, pages=None):
                return """
                Content here.

                Bibliography

                Reference 1.
                """

        extractor = ReferenceExtractor(MockBackend())
        text = MockBackend().extract_text(None)
        refs_section = extractor._find_references_section(text)

        assert refs_section is not None

    def test_parse_reference_extracts_year(self):
        """Should extract year from reference text."""

        class MockBackend:
            def extract_text(self, path, pages=None):
                return ""

        extractor = ReferenceExtractor(MockBackend())
        ref = extractor._parse_reference(
            "Smith, J. (2020). A paper about testing. Journal of Tests, 1, 1-10."
        )

        assert ref.year == 2020

    def test_parse_reference_extracts_doi(self):
        """Should extract DOI from reference text."""

        class MockBackend:
            def extract_text(self, path, pages=None):
                return ""

        extractor = ReferenceExtractor(MockBackend())
        ref = extractor._parse_reference(
            "Smith, J. (2020). A paper. doi: 10.1234/example.5678"
        )

        assert ref.doi == "10.1234/example.5678"

    def test_parse_reference_extracts_pages(self):
        """Should extract page range from reference text."""

        class MockBackend:
            def extract_text(self, path, pages=None):
                return ""

        extractor = ReferenceExtractor(MockBackend())
        ref = extractor._parse_reference(
            "Smith, J. (2020). A paper. Journal, 10, 123-456."
        )

        assert ref.pages == "123-456"
