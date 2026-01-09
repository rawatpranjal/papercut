"""PDF page rendering for vision LLM extraction."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RenderedPage:
    """A rendered PDF page as an image."""

    page_num: int  # 0-indexed
    image_data: bytes  # PNG bytes
    width: int
    height: int
    dpi: int


class PageRenderer:
    """Render PDF pages as PNG images for vision LLM processing.

    Uses PyMuPDF (fitz) for rendering, which must be installed
    via `pip install papercutter[fast]` or `pip install pymupdf`.
    """

    DEFAULT_DPI = 150  # Balance between quality and token cost

    def __init__(self, dpi: int = DEFAULT_DPI):
        """Initialize the renderer.

        Args:
            dpi: Resolution for rendering. Higher = better quality but more tokens.
                 150 DPI is typically sufficient for vision models.
        """
        self.dpi = dpi
        self._fitz = None

    def _ensure_fitz(self):
        """Ensure PyMuPDF is available."""
        if self._fitz is not None:
            return

        try:
            import fitz

            self._fitz = fitz
        except ImportError:
            raise ImportError(
                "Page rendering requires PyMuPDF. "
                "Install with: pip install papercutter[fast]"
            )

    def render_page(self, pdf_path: Path, page_num: int) -> RenderedPage:
        """Render a single page as a PNG image.

        Args:
            pdf_path: Path to the PDF file.
            page_num: 0-indexed page number.

        Returns:
            RenderedPage with PNG image data.

        Raises:
            ImportError: If PyMuPDF is not installed.
            ValueError: If page_num is out of range.
        """
        self._ensure_fitz()
        assert self._fitz is not None

        doc = self._fitz.open(pdf_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                raise ValueError(
                    f"Page {page_num} out of range (document has {len(doc)} pages)"
                )

            page = doc[page_num]
            mat = self._fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat)

            return RenderedPage(
                page_num=page_num,
                image_data=pix.tobytes("png"),
                width=pix.width,
                height=pix.height,
                dpi=self.dpi,
            )
        finally:
            doc.close()

    def render_region(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: tuple[float, float, float, float],
        padding: int = 20,
    ) -> RenderedPage:
        """Render a specific region of a page.

        Args:
            pdf_path: Path to the PDF file.
            page_num: 0-indexed page number.
            bbox: Bounding box (x0, y0, x1, y1) in PDF coordinates.
            padding: Pixels of padding around the region.

        Returns:
            RenderedPage with cropped PNG image data.
        """
        self._ensure_fitz()
        assert self._fitz is not None

        doc = self._fitz.open(pdf_path)
        try:
            page = doc[page_num]

            # Create rect with padding
            rect = self._fitz.Rect(
                bbox[0] - padding,
                bbox[1] - padding,
                bbox[2] + padding,
                bbox[3] + padding,
            )
            # Clip to page bounds
            rect = rect & page.rect

            mat = self._fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat, clip=rect)

            return RenderedPage(
                page_num=page_num,
                image_data=pix.tobytes("png"),
                width=pix.width,
                height=pix.height,
                dpi=self.dpi,
            )
        finally:
            doc.close()

    def render_pages(
        self,
        pdf_path: Path,
        page_nums: list[int] | None = None,
    ) -> list[RenderedPage]:
        """Render multiple pages.

        Args:
            pdf_path: Path to the PDF file.
            page_nums: 0-indexed page numbers to render. None = all pages.

        Returns:
            List of RenderedPage objects.
        """
        self._ensure_fitz()
        assert self._fitz is not None

        doc = self._fitz.open(pdf_path)
        try:
            if page_nums is None:
                page_nums = list(range(len(doc)))

            pages = []
            for page_num in page_nums:
                if 0 <= page_num < len(doc):
                    page = doc[page_num]
                    mat = self._fitz.Matrix(self.dpi / 72, self.dpi / 72)
                    pix = page.get_pixmap(matrix=mat)
                    pages.append(
                        RenderedPage(
                            page_num=page_num,
                            image_data=pix.tobytes("png"),
                            width=pix.width,
                            height=pix.height,
                            dpi=self.dpi,
                        )
                    )

            return pages
        finally:
            doc.close()

    def estimate_tokens(self, rendered: RenderedPage) -> int:
        """Estimate token count for a rendered page.

        Vision models typically encode images at ~1000 tokens per page
        at standard resolution.

        Args:
            rendered: A rendered page.

        Returns:
            Estimated token count.
        """
        # Rough estimate based on image dimensions
        # OpenAI charges based on 512x512 tiles
        tiles = ((rendered.width + 511) // 512) * ((rendered.height + 511) // 512)
        return tiles * 170  # ~170 tokens per tile
