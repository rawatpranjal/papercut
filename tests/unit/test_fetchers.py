"""Tests for paper fetchers."""

import pytest

from papercutter.legacy.fetchers.arxiv import ArxivFetcher
from papercutter.legacy.fetchers.doi import DOIFetcher
from papercutter.legacy.fetchers.nber import NBERFetcher
from papercutter.legacy.fetchers.ssrn import SSRNFetcher
from papercutter.legacy.fetchers.url import URLFetcher


class TestArxivFetcher:
    """Tests for ArxivFetcher."""

    @pytest.fixture
    def fetcher(self):
        return ArxivFetcher()

    @pytest.mark.parametrize(
        "identifier,expected",
        [
            ("2301.00001", True),
            ("2301.00001v2", True),
            ("arxiv:2301.00001", True),
            ("arXiv:2301.00001v2", True),
            ("hep-th/9901001", True),
            ("not-an-arxiv-id", False),
            ("10.1234/example", False),
            ("", False),
        ],
    )
    def test_can_handle(self, fetcher, identifier, expected):
        """Should correctly identify arXiv IDs."""
        assert fetcher.can_handle(identifier) == expected

    def test_normalize_id_removes_prefix(self, fetcher):
        """Should remove arxiv: prefix."""
        assert fetcher.normalize_id("arxiv:2301.00001") == "2301.00001"
        assert fetcher.normalize_id("arXiv:2301.00001v2") == "2301.00001v2"

    def test_normalize_id_preserves_bare_id(self, fetcher):
        """Should preserve bare IDs."""
        assert fetcher.normalize_id("2301.00001") == "2301.00001"

    def test_slugify(self, fetcher):
        """Should create URL-safe slugs."""
        assert fetcher._slugify("Hello World!") == "hello_world"
        assert fetcher._slugify("Test-Paper (2020)") == "test_paper_2020"


class TestDOIFetcher:
    """Tests for DOIFetcher."""

    @pytest.fixture
    def fetcher(self):
        return DOIFetcher()

    @pytest.mark.parametrize(
        "identifier,expected",
        [
            ("10.1234/example", True),
            ("10.1257/aer.20180779", True),
            ("doi:10.1234/example", True),
            ("https://doi.org/10.1234/example", True),
            ("https://dx.doi.org/10.1234/example", True),
            ("not-a-doi", False),
            ("2301.00001", False),
            ("", False),
        ],
    )
    def test_can_handle(self, fetcher, identifier, expected):
        """Should correctly identify DOIs."""
        assert fetcher.can_handle(identifier) == expected

    def test_normalize_id_extracts_doi(self, fetcher):
        """Should extract bare DOI from various formats."""
        assert fetcher.normalize_id("doi:10.1234/example") == "10.1234/example"
        assert (
            fetcher.normalize_id("https://doi.org/10.1234/example") == "10.1234/example"
        )
        assert fetcher.normalize_id("10.1234/example") == "10.1234/example"


class TestSSRNFetcher:
    """Tests for SSRNFetcher."""

    @pytest.fixture
    def fetcher(self):
        return SSRNFetcher()

    @pytest.mark.parametrize(
        "identifier,expected",
        [
            ("1234567", True),
            ("ssrn:1234567", True),
            ("SSRN-id1234567", True),
            ("12345678", True),
            ("123", False),  # Too short
            ("not-ssrn", False),
            ("", False),
        ],
    )
    def test_can_handle(self, fetcher, identifier, expected):
        """Should correctly identify SSRN IDs."""
        assert fetcher.can_handle(identifier) == expected

    def test_normalize_id_extracts_number(self, fetcher):
        """Should extract numeric ID."""
        assert fetcher.normalize_id("ssrn:1234567") == "1234567"
        assert fetcher.normalize_id("SSRN-id1234567") == "1234567"
        assert fetcher.normalize_id("1234567") == "1234567"


class TestNBERFetcher:
    """Tests for NBERFetcher."""

    @pytest.fixture
    def fetcher(self):
        return NBERFetcher()

    @pytest.mark.parametrize(
        "identifier,expected",
        [
            ("w29000", True),
            ("W29000", True),
            ("29000", True),
            ("nber:w29000", True),
            ("nber:29000", True),
            ("12345", True),
            ("not-nber", False),
            ("", False),
        ],
    )
    def test_can_handle(self, fetcher, identifier, expected):
        """Should correctly identify NBER IDs."""
        assert fetcher.can_handle(identifier) == expected

    def test_normalize_id_extracts_number(self, fetcher):
        """Should extract numeric ID."""
        assert fetcher.normalize_id("w29000") == "29000"
        assert fetcher.normalize_id("nber:w29000") == "29000"
        assert fetcher.normalize_id("29000") == "29000"


class TestURLFetcher:
    """Tests for URLFetcher."""

    @pytest.fixture
    def fetcher(self):
        return URLFetcher()

    @pytest.mark.parametrize(
        "identifier,expected",
        [
            ("https://example.com/paper.pdf", True),
            ("http://example.com/paper.pdf", True),
            ("https://arxiv.org/pdf/2301.00001.pdf", True),
            ("ftp://example.com/paper.pdf", False),
            ("example.com/paper.pdf", False),
            ("", False),
        ],
    )
    def test_can_handle(self, fetcher, identifier, expected):
        """Should correctly identify HTTP URLs."""
        assert fetcher.can_handle(identifier) == expected

    def test_filename_from_url_with_pdf(self, fetcher):
        """Should extract filename from URL with .pdf extension."""
        filename = fetcher._filename_from_url("https://example.com/my-paper.pdf")
        assert filename == "my-paper.pdf"

    def test_filename_from_url_without_pdf(self, fetcher):
        """Should generate filename for non-PDF URLs."""
        filename = fetcher._filename_from_url("https://example.com/download/12345")
        assert filename.endswith(".pdf")
        assert "example" in filename
