"""Figure extraction from PDFs."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractedFigure:
    """An extracted figure from a PDF."""

    id: int
    page: int  # 1-indexed
    width: int
    height: int
    image_data: bytes
    format: str = "png"
    caption: str | None = None

    def save(self, output_path: Path) -> Path:
        """Save figure to file.

        Args:
            output_path: Output file path.

        Returns:
            Path to saved file.
        """
        output_path.write_bytes(self.image_data)
        return output_path

    def to_dict(self) -> dict:
        """Convert to dictionary (without image data)."""
        return {
            "id": self.id,
            "page": self.page,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "caption": self.caption,
        }


class FigureExtractor:
    """Extract figures/images from PDF files.

    Uses PyMuPDF (fitz) for image extraction.
    Falls back gracefully if not installed.
    """

    MIN_WIDTH = 100  # Minimum width to consider as figure
    MIN_HEIGHT = 100  # Minimum height to consider as figure

    def __init__(
        self,
        min_width: int = MIN_WIDTH,
        min_height: int = MIN_HEIGHT,
    ):
        """Initialize the figure extractor.

        Args:
            min_width: Minimum width for figures.
            min_height: Minimum height for figures.
        """
        self.min_width = min_width
        self.min_height = min_height
        self._fitz_available = self._check_fitz()

    def _check_fitz(self) -> bool:
        """Check if PyMuPDF is available."""
        try:
            import fitz
            return True
        except ImportError:
            return False

    def extract(
        self,
        pdf_path: Path,
        pages: list[int] | None = None,
    ) -> list[ExtractedFigure]:
        """Extract figures from a PDF.

        Args:
            pdf_path: Path to PDF file.
            pages: Optional list of 0-indexed page numbers.

        Returns:
            List of extracted figures.

        Raises:
            ImportError: If PyMuPDF is not installed.
        """
        if not self._fitz_available:
            raise ImportError(
                "PyMuPDF (fitz) is required for figure extraction. "
                "Install with: pip install pymupdf"
            )

        import fitz

        figures = []
        figure_id = 0

        doc = fitz.open(pdf_path)

        page_range = pages if pages else range(len(doc))

        for page_num in page_range:
            if page_num >= len(doc):
                continue

            page = doc[page_num]
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]

                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    width = base_image["width"]
                    height = base_image["height"]
                    ext = base_image["ext"]

                    # Filter small images (likely icons/logos)
                    if width < self.min_width or height < self.min_height:
                        continue

                    figure_id += 1

                    # Convert to PNG if needed
                    if ext != "png":
                        image_bytes = self._convert_to_png(image_bytes, ext)
                        ext = "png"

                    figures.append(ExtractedFigure(
                        id=figure_id,
                        page=page_num + 1,  # 1-indexed
                        width=width,
                        height=height,
                        image_data=image_bytes,
                        format=ext,
                    ))

                except Exception:
                    # Skip problematic images
                    continue

        doc.close()
        return figures

    def extract_one(
        self,
        pdf_path: Path,
        figure_id: int,
    ) -> ExtractedFigure | None:
        """Extract a single figure by ID.

        Args:
            pdf_path: Path to PDF file.
            figure_id: Figure ID (1-indexed).

        Returns:
            ExtractedFigure or None if not found.
        """
        figures = self.extract(pdf_path)
        for fig in figures:
            if fig.id == figure_id:
                return fig
        return None

    def _convert_to_png(self, image_bytes: bytes, source_format: str) -> bytes:
        """Convert image to PNG format.

        Args:
            image_bytes: Source image data.
            source_format: Source format.

        Returns:
            PNG image data.
        """
        try:
            import fitz

            # Use PyMuPDF's pixmap for conversion
            pix = fitz.Pixmap(image_bytes)
            png_data = pix.tobytes("png")
            return png_data
        except Exception:
            # Return original if conversion fails
            return image_bytes

    def is_available(self) -> bool:
        """Check if figure extraction is available."""
        return self._fitz_available
