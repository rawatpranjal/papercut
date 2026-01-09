"""Nougat-based equation converter (free, local)."""

from typing import Any

from papercutter.converters.base import BaseConverter
from papercutter.core.equations import LaTeXConversion


class NougatConverter(BaseConverter):
    """Convert equations using Nougat model.

    Nougat is a transformer-based model for OCR of scientific documents.
    Runs locally, no API key required.

    Installation: pip install nougat-ocr
    """

    def __init__(self, model_name: str = "facebook/nougat-small"):
        """Initialize the Nougat converter.

        Args:
            model_name: Name of the Nougat model to use.
        """
        self._model_name = model_name
        self._model: Any | None = None
        self._processor: Any | None = None
        self._available = self._check_nougat()

    def _check_nougat(self) -> bool:
        """Check if nougat dependencies are available."""
        try:
            import torch  # noqa: F401
            from transformers import (  # noqa: F401
                NougatProcessor,
                VisionEncoderDecoderModel,
            )

            return True
        except ImportError:
            return False

    def _ensure_model(self) -> None:
        """Lazy load nougat model."""
        if self._model is not None:
            return

        if not self._available:
            raise ImportError(
                "Nougat requires transformers and torch. "
                "Install with: pip install 'papercutter[equations-nougat]'"
            )

        import sys

        from transformers import NougatProcessor, VisionEncoderDecoderModel

        # Warn user about potential model download
        print(
            f"Loading Nougat model '{self._model_name}' "
            "(this may download ~1GB on first run)...",
            file=sys.stderr,
        )

        try:
            self._processor = NougatProcessor.from_pretrained(self._model_name)
            self._model = VisionEncoderDecoderModel.from_pretrained(self._model_name)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Nougat model '{self._model_name}': {e}\n"
                "Ensure you have internet access for first-time model download."
            ) from e

    def convert(self, image_data: bytes) -> LaTeXConversion:
        """Convert equation image to LaTeX using Nougat.

        Args:
            image_data: PNG image bytes.

        Returns:
            LaTeXConversion with result.

        Raises:
            ImportError: If Nougat is not installed.
            Exception: If conversion fails.
        """
        self._ensure_model()

        from io import BytesIO

        import torch
        from PIL import Image

        # Convert bytes to PIL Image
        image = Image.open(BytesIO(image_data)).convert("RGB")

        # Type assertions after _ensure_model
        assert self._processor is not None
        assert self._model is not None

        # Process image
        pixel_values = self._processor(image, return_tensors="pt").pixel_values

        # Generate LaTeX
        with torch.no_grad():
            outputs = self._model.generate(
                pixel_values,
                max_length=512,
                num_beams=4,
                early_stopping=True,
            )

        # Decode output
        latex = self._processor.batch_decode(outputs, skip_special_tokens=True)[0]

        # Clean up the LaTeX
        latex = latex.strip()

        # Estimate confidence based on output characteristics
        # This is a heuristic - actual confidence would require model internals
        confidence = self._estimate_confidence(latex)

        return LaTeXConversion(
            latex=latex,
            confidence=confidence,
            method="nougat",
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

        confidence = 0.85  # Base confidence for Nougat

        # Penalize very short output
        if len(latex) < 3:
            confidence -= 0.3

        # Penalize if it looks like an error or placeholder
        error_indicators = ["[MISSING]", "[ERROR]", "???", "..."]
        if any(ind in latex for ind in error_indicators):
            confidence -= 0.3

        # Boost if it has typical LaTeX structure
        latex_indicators = ["\\", "{", "}", "^", "_"]
        latex_count = sum(1 for c in latex if c in latex_indicators)
        if latex_count > 2:
            confidence += 0.05

        return max(0.0, min(1.0, confidence))

    def is_available(self) -> bool:
        """Check if Nougat is available."""
        return self._available

    @property
    def name(self) -> str:
        """Return converter name."""
        return "nougat"
