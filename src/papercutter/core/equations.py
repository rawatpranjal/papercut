"""Equation extraction from PDFs."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from papercutter.converters.base import BaseConverter


class EquationType(str, Enum):
    """Type of equation."""

    INLINE = "inline"
    DISPLAY = "display"


@dataclass
class EquationBbox:
    """Bounding box for an equation region."""

    x0: float
    y0: float
    x1: float
    y1: float

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}

    @property
    def width(self) -> float:
        """Width of the bounding box."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Height of the bounding box."""
        return self.y1 - self.y0

    @property
    def center_x(self) -> float:
        """X coordinate of center."""
        return (self.x0 + self.x1) / 2


@dataclass
class LaTeXConversion:
    """Result of image-to-LaTeX conversion."""

    latex: str
    confidence: float  # 0.0 to 1.0
    method: str  # "nougat", "pix2tex", "mathpix"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "latex": self.latex,
            "confidence": self.confidence,
            "method": self.method,
        }


@dataclass
class ExtractedEquation:
    """An extracted equation from a PDF."""

    id: int
    page: int  # 1-indexed
    type: EquationType
    bbox: EquationBbox
    image_data: bytes
    image_path: Path | None = None
    context: str | None = None
    latex: LaTeXConversion | None = None
    format: str = "png"

    def save(self, output_path: Path) -> Path:
        """Save equation image to file.

        Args:
            output_path: Output file path.

        Returns:
            Path to saved file.
        """
        output_path.write_bytes(self.image_data)
        self.image_path = output_path
        return output_path

    def to_dict(self, include_image_data: bool = False) -> dict[str, Any]:
        """Convert to dictionary for JSON output.

        Args:
            include_image_data: Whether to include base64-encoded image data.

        Returns:
            Dictionary representation.
        """
        result: dict[str, Any] = {
            "id": self.id,
            "page": self.page,
            "type": self.type.value,
            "bbox": self.bbox.to_dict(),
            "format": self.format,
        }
        if self.image_path:
            result["image_path"] = str(self.image_path)
        if self.context:
            result["context"] = self.context
        if self.latex:
            result["latex"] = self.latex.to_dict()
        if include_image_data:
            import base64

            result["image_base64"] = base64.b64encode(self.image_data).decode()
        return result

    @property
    def is_low_confidence(self) -> bool:
        """Check if LaTeX conversion has low confidence."""
        if self.latex is None:
            return False
        return self.latex.confidence < 0.8


@dataclass
class EquationExtractionResult:
    """Result of equation extraction from a document."""

    equations: list[ExtractedEquation]
    pages_processed: list[int]
    method: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        low_confidence_count = sum(1 for eq in self.equations if eq.is_low_confidence)
        result: dict[str, Any] = {
            "count": len(self.equations),
            "pages_processed": self.pages_processed,
            "method": self.method,
            "low_confidence_count": low_confidence_count,
            "equations": [eq.to_dict() for eq in self.equations],
        }
        if self.errors:
            result["errors"] = self.errors
        return result


class EquationExtractor:
    """Extract equations from PDF files.

    Uses PyMuPDF (fitz) for detection and image extraction.
    Optionally converts to LaTeX using Nougat, pix2tex, or MathPix.
    """

    MIN_WIDTH = 50
    MIN_HEIGHT = 20
    DEFAULT_DPI = 300
    DEFAULT_PADDING = 5

    # Math-related font name patterns (lowercase for matching)
    MATH_FONTS = frozenset({
        "cmex",
        "cmsy",
        "cmmi",
        "cmmib",
        "cmr",
        "symbol",
        "symbolmt",
        "mt extra",
        "euex",
        "eufm",
        "stixmath",
        "cambria math",
        "asana-math",
        "xits math",
        "latinmodern-math",
        "tex gyre",
        "newcm",
        "libertinus math",
    })

    # Unicode math symbols for detection
    MATH_SYMBOLS = frozenset(
        # Basic math operators
        "+-*/=<>"
        # Greek letters commonly used in math
        "\u03b1\u03b2\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8\u03b9\u03ba\u03bb\u03bc"
        "\u03bd\u03be\u03bf\u03c0\u03c1\u03c2\u03c3\u03c4\u03c5\u03c6\u03c7\u03c8\u03c9"
        # Mathematical operators and symbols
        "\u2200\u2201\u2202\u2203\u2204\u2205\u2206\u2207\u2208\u2209\u220a\u220b\u220c"
        "\u220d\u220e\u220f\u2210\u2211\u2212\u2213\u2214\u2215\u2216\u2217\u2218\u2219"
        "\u221a\u221b\u221c\u221d\u221e\u221f\u2220\u2221\u2222\u2223\u2224\u2225\u2226"
        "\u2227\u2228\u2229\u222a\u222b\u222c\u222d\u222e\u222f\u2230\u2231\u2232\u2233"
        "\u2234\u2235\u2236\u2237\u2238\u2239\u223a\u223b\u223c\u223d\u223e\u223f"
        "\u2260\u2261\u2262\u2263\u2264\u2265\u2266\u2267\u2268\u2269\u226a\u226b"
        "\u2282\u2283\u2284\u2285\u2286\u2287\u2288\u2289\u228a\u228b"
        # Superscripts and subscripts
        "\u00b2\u00b3\u00b9\u2070\u2071\u2074\u2075\u2076\u2077\u2078\u2079"
        "\u207a\u207b\u207c\u207d\u207e\u207f"
        "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089"
        # Fractions and other
        "\u00bc\u00bd\u00be\u2153\u2154\u00d7\u00f7"
    )

    def __init__(
        self,
        converter: Optional["BaseConverter"] = None,
        min_width: int = MIN_WIDTH,
        min_height: int = MIN_HEIGHT,
        dpi: int = DEFAULT_DPI,
        detect_inline: bool = True,
        padding: int = DEFAULT_PADDING,
    ):
        """Initialize the equation extractor.

        Args:
            converter: Optional LaTeX converter (Nougat, pix2tex, MathPix).
            min_width: Minimum width for detected equations.
            min_height: Minimum height for detected equations.
            dpi: DPI for image extraction.
            detect_inline: Whether to detect inline equations.
            padding: Padding around equation regions in pixels.
        """
        self.converter = converter
        self.min_width = min_width
        self.min_height = min_height
        self.dpi = dpi
        self.detect_inline = detect_inline
        self.padding = padding
        self._fitz_available = self._check_fitz()

    def _check_fitz(self) -> bool:
        """Check if PyMuPDF is available."""
        try:
            import fitz  # noqa: F401

            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        """Check if equation extraction is available."""
        return self._fitz_available

    def extract(
        self,
        pdf_path: Path,
        pages: list[int] | None = None,
        extract_latex: bool = True,
        min_confidence: float = 0.0,
    ) -> EquationExtractionResult:
        """Extract equations from a PDF.

        Args:
            pdf_path: Path to PDF file.
            pages: Optional list of 0-indexed page numbers.
            extract_latex: Whether to attempt LaTeX conversion.
            min_confidence: Minimum confidence for LaTeX results.

        Returns:
            EquationExtractionResult with detected equations.

        Raises:
            ImportError: If PyMuPDF is not installed.
        """
        if not self._fitz_available:
            raise ImportError(
                "PyMuPDF (fitz) is required for equation extraction. "
                "Install with: pip install pymupdf"
            )

        import fitz

        equations: list[ExtractedEquation] = []
        errors: list[str] = []
        equation_id = 0

        doc = fitz.open(pdf_path)
        page_range = pages if pages is not None else list(range(len(doc)))
        pages_processed = []

        for page_num in page_range:
            if page_num < 0 or page_num >= len(doc):
                continue

            pages_processed.append(page_num)
            page = doc[page_num]

            # Detect equations on this page
            detected = self._detect_equations_on_page(page, page_num)

            for detection in detected:
                equation_id += 1

                try:
                    # Extract image region
                    image_data = self._extract_region_as_image(page, detection["bbox"])

                    # Get surrounding context
                    context = self._extract_context(page, detection["bbox"])

                    equation = ExtractedEquation(
                        id=equation_id,
                        page=page_num + 1,  # 1-indexed
                        type=detection["type"],
                        bbox=EquationBbox(**detection["bbox"]),
                        image_data=image_data,
                        context=context,
                    )

                    # Convert to LaTeX if converter available and requested
                    if extract_latex and self.converter is not None:
                        try:
                            latex_result = self.converter.convert(image_data)
                            if latex_result.confidence >= min_confidence:
                                equation.latex = latex_result
                        except Exception as e:
                            errors.append(f"LaTeX conversion failed for eq {equation_id}: {e}")

                    equations.append(equation)

                except Exception as e:
                    errors.append(f"Failed to extract equation on page {page_num + 1}: {e}")

        doc.close()

        return EquationExtractionResult(
            equations=equations,
            pages_processed=[p + 1 for p in pages_processed],  # Convert to 1-indexed for user display
            method=self.converter.name if self.converter else None,
            errors=errors,
        )

    def _detect_equations_on_page(self, page: Any, page_num: int) -> list[dict[str, Any]]:
        """Detect equation regions on a page.

        Uses multiple heuristics:
        1. Font analysis (math fonts like CMEX, CMSY, Symbol)
        2. Unicode math symbol density
        3. Layout patterns (centered blocks for display equations)

        Args:
            page: PyMuPDF page object.
            page_num: 0-indexed page number.

        Returns:
            List of {"bbox": {...}, "type": EquationType}
        """
        import fitz

        detected: list[dict[str, Any]] = []
        page_width = page.rect.width

        # Get all text with font info
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        # Collect math spans
        math_spans: list[dict[str, Any]] = []

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span.get("text", "")
                    font = span.get("font", "")
                    bbox = span.get("bbox", (0, 0, 0, 0))

                    is_math = self._is_math_font(font) or self._has_math_symbols(text)

                    if is_math:
                        math_spans.append({
                            "bbox": bbox,
                            "text": text,
                            "font": font,
                        })

        # Merge adjacent math spans into equation regions
        merged = self._merge_adjacent_spans(math_spans)

        # Classify and filter
        for region in merged:
            bbox = region["bbox"]
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]

            # Filter by minimum size
            if width < self.min_width or height < self.min_height:
                continue

            # Classify as display or inline
            bbox_dict = {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]}
            eq_type = (
                EquationType.DISPLAY
                if self._is_display_equation(bbox_dict, page_width)
                else EquationType.INLINE
            )

            # Skip inline if not requested
            if eq_type == EquationType.INLINE and not self.detect_inline:
                continue

            detected.append({
                "bbox": bbox_dict,
                "type": eq_type,
            })

        return detected

    def _is_math_font(self, fontname: str) -> bool:
        """Check if font is a math-related font.

        Args:
            fontname: Font name from PDF.

        Returns:
            True if font appears to be a math font.
        """
        if not fontname:
            return False
        fontname_lower = fontname.lower()
        return any(mf in fontname_lower for mf in self.MATH_FONTS)

    def _has_math_symbols(self, text: str, threshold: float = 0.15) -> bool:
        """Check if text has high density of math symbols.

        Args:
            text: Text to check.
            threshold: Minimum ratio of math symbols.

        Returns:
            True if text has significant math content.
        """
        if not text or len(text) < 2:
            return False

        math_count = sum(1 for c in text if c in self.MATH_SYMBOLS)
        return (math_count / len(text)) >= threshold

    def _is_display_equation(self, bbox: dict[str, float], page_width: float) -> bool:
        """Detect if bbox represents a centered display equation.

        Args:
            bbox: Bounding box dictionary.
            page_width: Width of the page.

        Returns:
            True if bbox appears to be a display equation.
        """
        # Check horizontal centering (within 15% of center)
        center = (bbox["x0"] + bbox["x1"]) / 2
        page_center = page_width / 2
        centered = abs(center - page_center) < page_width * 0.15

        # Check if equation spans less than 80% of page width
        # (display equations are usually not full-width)
        eq_width = bbox["x1"] - bbox["x0"]
        reasonable_width = eq_width < page_width * 0.8

        return centered and reasonable_width

    def _merge_adjacent_spans(
        self, spans: list[dict[str, Any]], tolerance: float = 5.0
    ) -> list[dict[str, Any]]:
        """Merge adjacent math spans into equation regions.

        Args:
            spans: List of span dictionaries with bbox.
            tolerance: Maximum gap between spans to merge.

        Returns:
            List of merged regions.
        """
        if not spans:
            return []

        # Sort by y position then x position
        sorted_spans = sorted(spans, key=lambda s: (s["bbox"][1], s["bbox"][0]))

        merged: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None

        for span in sorted_spans:
            bbox = span["bbox"]

            if current is None:
                current = {
                    "bbox": list(bbox),
                    "texts": [span.get("text", "")],
                }
            else:
                curr_bbox = current["bbox"]

                # Check if spans are adjacent (same line or close vertically)
                same_line = abs(bbox[1] - curr_bbox[1]) < tolerance
                horizontally_close = bbox[0] - curr_bbox[2] < tolerance * 3
                vertically_adjacent = (
                    bbox[1] - curr_bbox[3] < tolerance and bbox[1] - curr_bbox[3] >= 0
                )

                if (same_line and horizontally_close) or vertically_adjacent:
                    # Merge: expand bounding box
                    curr_bbox[0] = min(curr_bbox[0], bbox[0])
                    curr_bbox[1] = min(curr_bbox[1], bbox[1])
                    curr_bbox[2] = max(curr_bbox[2], bbox[2])
                    curr_bbox[3] = max(curr_bbox[3], bbox[3])
                    current["texts"].append(span.get("text", ""))
                else:
                    # Start new region
                    merged.append(current)
                    current = {
                        "bbox": list(bbox),
                        "texts": [span.get("text", "")],
                    }

        if current:
            merged.append(current)

        return merged

    def _extract_region_as_image(self, page: Any, bbox: dict[str, float]) -> bytes:
        """Extract a region of the page as a high-res PNG image.

        Args:
            page: PyMuPDF page object.
            bbox: Bounding box dictionary.

        Returns:
            PNG image data as bytes.
        """
        import fitz

        # Create clip rect with padding
        rect = fitz.Rect(
            bbox["x0"] - self.padding,
            bbox["y0"] - self.padding,
            bbox["x1"] + self.padding,
            bbox["y1"] + self.padding,
        )

        # Clip to page bounds
        rect = rect & page.rect

        # Render at high DPI
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        pix = page.get_pixmap(matrix=mat, clip=rect)

        return pix.tobytes("png")

    def _extract_context(
        self, page: Any, bbox: dict[str, float], chars: int = 100
    ) -> str | None:
        """Extract surrounding text context for an equation.

        Args:
            page: PyMuPDF page object.
            bbox: Bounding box of the equation.
            chars: Approximate number of characters to extract.

        Returns:
            Context string or None if not found.
        """
        import fitz

        # Get text above the equation
        above_rect = fitz.Rect(
            page.rect.x0,
            max(bbox["y0"] - 50, 0),
            page.rect.x1,
            bbox["y0"],
        )

        above_text = page.get_text("text", clip=above_rect).strip()

        if above_text:
            # Take last portion
            if len(above_text) > chars:
                above_text = "..." + above_text[-chars:]
            return above_text

        return None
