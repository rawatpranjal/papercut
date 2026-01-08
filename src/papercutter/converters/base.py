"""Base class for equation-to-LaTeX converters."""

from abc import ABC, abstractmethod

from papercutter.core.equations import LaTeXConversion


class BaseConverter(ABC):
    """Abstract base class for equation converters.

    Converters take equation images and produce LaTeX representations
    with confidence scores.
    """

    @abstractmethod
    def convert(self, image_data: bytes) -> LaTeXConversion:
        """Convert equation image to LaTeX.

        Args:
            image_data: PNG image bytes.

        Returns:
            LaTeXConversion with result.

        Raises:
            Exception: If conversion fails.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if converter is available.

        Returns:
            True if the converter can be used.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return converter name.

        Returns:
            Name of the converter (e.g., "nougat", "pix2tex", "mathpix").
        """
        pass
