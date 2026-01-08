"""pix2tex-based equation converter (free, local)."""

from typing import Any

from papercutter.converters.base import BaseConverter
from papercutter.core.equations import LaTeXConversion


class Pix2TexConverter(BaseConverter):
    """Convert equations using pix2tex model.

    pix2tex is a lightweight model for LaTeX OCR.
    Runs locally, no API key required.

    Installation: pip install pix2tex
    """

    def __init__(self):
        """Initialize the pix2tex converter."""
        self._model: Any | None = None
        self._available = self._check_pix2tex()

    def _check_pix2tex(self) -> bool:
        """Check if pix2tex is available."""
        try:
            from pix2tex.cli import LatexOCR  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_model(self) -> None:
        """Lazy load pix2tex model."""
        if self._model is not None:
            return

        if not self._available:
            raise ImportError(
                "pix2tex is required for this converter. "
                "Install with: pip install pix2tex"
            )

        from pix2tex.cli import LatexOCR

        self._model = LatexOCR()

    def convert(self, image_data: bytes) -> LaTeXConversion:
        """Convert equation image to LaTeX using pix2tex.

        Args:
            image_data: PNG image bytes.

        Returns:
            LaTeXConversion with result.

        Raises:
            ImportError: If pix2tex is not installed.
            Exception: If conversion fails.
        """
        self._ensure_model()

        from io import BytesIO

        from PIL import Image

        # Convert bytes to PIL Image
        image = Image.open(BytesIO(image_data)).convert("RGB")

        # Run inference
        latex = self._model(image)

        # Clean up the LaTeX
        latex = latex.strip()

        # Estimate confidence
        confidence = self._estimate_confidence(latex)

        return LaTeXConversion(
            latex=latex,
            confidence=confidence,
            method="pix2tex",
        )

    def _estimate_confidence(self, latex: str) -> float:
        """Estimate confidence based on output characteristics.

        Args:
            latex: Generated LaTeX string.

        Returns:
            Estimated confidence between 0.0 and 1.0.
        """
        if not latex:
            return 0.0

        confidence = 0.80  # Base confidence for pix2tex (slightly lower than Nougat)

        # Penalize very short output
        if len(latex) < 3:
            confidence -= 0.3

        # Penalize if it looks like an error
        if "error" in latex.lower() or "???" in latex:
            confidence -= 0.3

        # Boost if it has typical LaTeX structure
        latex_indicators = ["\\", "{", "}", "^", "_"]
        latex_count = sum(1 for c in latex if c in latex_indicators)
        if latex_count > 2:
            confidence += 0.05

        return max(0.0, min(1.0, confidence))

    def is_available(self) -> bool:
        """Check if pix2tex is available."""
        return self._available

    @property
    def name(self) -> str:
        """Return converter name."""
        return "pix2tex"
