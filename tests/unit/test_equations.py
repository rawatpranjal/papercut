"""Tests for equation extraction."""

import pytest

from papercutter.core.equations import (
    EquationBbox,
    EquationExtractor,
    EquationType,
    ExtractedEquation,
    LaTeXConversion,
)


class TestEquationBbox:
    """Tests for EquationBbox dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        bbox = EquationBbox(x0=10.0, y0=20.0, x1=100.0, y1=50.0)
        result = bbox.to_dict()
        assert result == {"x0": 10.0, "y0": 20.0, "x1": 100.0, "y1": 50.0}

    def test_width_property(self):
        """Should calculate width correctly."""
        bbox = EquationBbox(x0=10.0, y0=20.0, x1=100.0, y1=50.0)
        assert bbox.width == 90.0

    def test_height_property(self):
        """Should calculate height correctly."""
        bbox = EquationBbox(x0=10.0, y0=20.0, x1=100.0, y1=50.0)
        assert bbox.height == 30.0

    def test_center_x_property(self):
        """Should calculate center x correctly."""
        bbox = EquationBbox(x0=10.0, y0=20.0, x1=100.0, y1=50.0)
        assert bbox.center_x == 55.0


class TestLaTeXConversion:
    """Tests for LaTeXConversion dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        latex = LaTeXConversion(
            latex=r"\frac{a}{b}",
            confidence=0.95,
            method="nougat",
        )
        result = latex.to_dict()
        assert result["latex"] == r"\frac{a}{b}"
        assert result["confidence"] == 0.95
        assert result["method"] == "nougat"


class TestExtractedEquation:
    """Tests for ExtractedEquation dataclass."""

    def test_to_dict_basic(self):
        """Should convert to dictionary with basic fields."""
        eq = ExtractedEquation(
            id=1,
            page=5,
            type=EquationType.DISPLAY,
            bbox=EquationBbox(10, 20, 100, 50),
            image_data=b"fake_png_data",
        )
        result = eq.to_dict()
        assert result["id"] == 1
        assert result["page"] == 5
        assert result["type"] == "display"
        assert result["format"] == "png"
        assert "image_base64" not in result

    def test_to_dict_with_latex(self):
        """Should include latex when present."""
        eq = ExtractedEquation(
            id=1,
            page=5,
            type=EquationType.DISPLAY,
            bbox=EquationBbox(10, 20, 100, 50),
            image_data=b"fake_png_data",
            latex=LaTeXConversion(latex=r"E = mc^2", confidence=0.9, method="test"),
        )
        result = eq.to_dict()
        assert result["latex"]["latex"] == r"E = mc^2"
        assert result["latex"]["confidence"] == 0.9

    def test_to_dict_with_context(self):
        """Should include context when present."""
        eq = ExtractedEquation(
            id=1,
            page=5,
            type=EquationType.INLINE,
            bbox=EquationBbox(10, 20, 100, 50),
            image_data=b"fake_png_data",
            context="as shown in equation",
        )
        result = eq.to_dict()
        assert result["context"] == "as shown in equation"

    def test_to_dict_with_image_data(self):
        """Should include base64 image data when requested."""
        eq = ExtractedEquation(
            id=1,
            page=5,
            type=EquationType.DISPLAY,
            bbox=EquationBbox(10, 20, 100, 50),
            image_data=b"fake_png_data",
        )
        result = eq.to_dict(include_image_data=True)
        assert "image_base64" in result
        import base64

        assert base64.b64decode(result["image_base64"]) == b"fake_png_data"

    def test_is_low_confidence_true(self):
        """Should return True when confidence is below 0.8."""
        eq = ExtractedEquation(
            id=1,
            page=1,
            type=EquationType.DISPLAY,
            bbox=EquationBbox(0, 0, 100, 50),
            image_data=b"",
            latex=LaTeXConversion(latex="x", confidence=0.5, method="test"),
        )
        assert eq.is_low_confidence is True

    def test_is_low_confidence_false(self):
        """Should return False when confidence is 0.8 or above."""
        eq = ExtractedEquation(
            id=1,
            page=1,
            type=EquationType.DISPLAY,
            bbox=EquationBbox(0, 0, 100, 50),
            image_data=b"",
            latex=LaTeXConversion(latex="x", confidence=0.9, method="test"),
        )
        assert eq.is_low_confidence is False

    def test_is_low_confidence_no_latex(self):
        """Should return False when no latex present."""
        eq = ExtractedEquation(
            id=1,
            page=1,
            type=EquationType.DISPLAY,
            bbox=EquationBbox(0, 0, 100, 50),
            image_data=b"",
        )
        assert eq.is_low_confidence is False

    def test_save(self, tmp_path):
        """Should save image data to file."""
        eq = ExtractedEquation(
            id=1,
            page=1,
            type=EquationType.DISPLAY,
            bbox=EquationBbox(0, 0, 100, 50),
            image_data=b"test_image_data",
        )
        output_path = tmp_path / "test_eq.png"
        result = eq.save(output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == b"test_image_data"
        assert eq.image_path == output_path


class TestEquationExtractor:
    """Tests for EquationExtractor class."""

    def test_is_math_font_positive(self):
        """Should identify math fonts."""
        extractor = EquationExtractor()
        assert extractor._is_math_font("CMEX10") is True
        assert extractor._is_math_font("Symbol") is True
        assert extractor._is_math_font("Cambria Math") is True
        assert extractor._is_math_font("CMSY10") is True

    def test_is_math_font_negative(self):
        """Should reject non-math fonts."""
        extractor = EquationExtractor()
        assert extractor._is_math_font("Times-Roman") is False
        assert extractor._is_math_font("Arial") is False
        assert extractor._is_math_font("Helvetica") is False

    def test_is_math_font_empty(self):
        """Should handle empty string."""
        extractor = EquationExtractor()
        assert extractor._is_math_font("") is False

    def test_has_math_symbols_positive(self):
        """Should detect math symbol content."""
        extractor = EquationExtractor()
        assert extractor._has_math_symbols("∑∫∂") is True
        assert extractor._has_math_symbols("x ∈ ℝ") is True
        assert extractor._has_math_symbols("α + β = γ") is True

    def test_has_math_symbols_negative(self):
        """Should reject text without math symbols."""
        extractor = EquationExtractor()
        assert extractor._has_math_symbols("hello world") is False
        assert extractor._has_math_symbols("This is a sentence.") is False

    def test_has_math_symbols_empty(self):
        """Should handle empty or very short strings."""
        extractor = EquationExtractor()
        assert extractor._has_math_symbols("") is False
        assert extractor._has_math_symbols("x") is False

    def test_is_display_equation_centered(self):
        """Should identify centered display equations."""
        extractor = EquationExtractor()
        page_width = 612.0  # Standard letter width

        # Centered equation
        bbox = {"x0": 200, "y0": 100, "x1": 412, "y1": 150}
        assert extractor._is_display_equation(bbox, page_width) is True

    def test_is_display_equation_not_centered(self):
        """Should reject non-centered equations."""
        extractor = EquationExtractor()
        page_width = 612.0

        # Left-aligned (not centered)
        bbox = {"x0": 72, "y0": 100, "x1": 200, "y1": 150}
        assert extractor._is_display_equation(bbox, page_width) is False

    def test_is_display_equation_too_wide(self):
        """Should reject full-width content."""
        extractor = EquationExtractor()
        page_width = 612.0

        # Full-width content (not a display equation)
        bbox = {"x0": 50, "y0": 100, "x1": 562, "y1": 150}
        assert extractor._is_display_equation(bbox, page_width) is False

    def test_merge_adjacent_spans_single(self):
        """Should handle single span."""
        extractor = EquationExtractor()
        spans = [{"bbox": (10, 20, 100, 40), "text": "x"}]
        result = extractor._merge_adjacent_spans(spans)
        assert len(result) == 1

    def test_merge_adjacent_spans_multiple_same_line(self):
        """Should merge spans on same line."""
        extractor = EquationExtractor()
        spans = [
            {"bbox": (10, 20, 50, 40), "text": "x"},
            {"bbox": (52, 20, 100, 40), "text": "+"},
            {"bbox": (102, 20, 150, 40), "text": "y"},
        ]
        result = extractor._merge_adjacent_spans(spans)
        assert len(result) == 1
        # Check merged bbox encompasses all spans
        assert result[0]["bbox"][0] == 10  # x0
        assert result[0]["bbox"][2] == 150  # x1

    def test_merge_adjacent_spans_different_lines(self):
        """Should not merge spans on different lines."""
        extractor = EquationExtractor()
        spans = [
            {"bbox": (10, 20, 100, 40), "text": "line1"},
            {"bbox": (10, 100, 100, 120), "text": "line2"},  # Different y
        ]
        result = extractor._merge_adjacent_spans(spans)
        assert len(result) == 2

    def test_merge_adjacent_spans_empty(self):
        """Should handle empty list."""
        extractor = EquationExtractor()
        result = extractor._merge_adjacent_spans([])
        assert result == []

    def test_is_available_when_fitz_missing(self):
        """Should return False when PyMuPDF not available."""
        extractor = EquationExtractor()
        extractor._fitz_available = False
        assert extractor.is_available() is False

    def test_extract_raises_when_fitz_unavailable(self, tmp_path):
        """Should raise ImportError when PyMuPDF not available."""
        extractor = EquationExtractor()
        extractor._fitz_available = False

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        with pytest.raises(ImportError) as exc_info:
            extractor.extract(pdf_path)

        assert "PyMuPDF" in str(exc_info.value)


class TestEquationType:
    """Tests for EquationType enum."""

    def test_display_value(self):
        """Should have correct string value for display."""
        assert EquationType.DISPLAY.value == "display"

    def test_inline_value(self):
        """Should have correct string value for inline."""
        assert EquationType.INLINE.value == "inline"
