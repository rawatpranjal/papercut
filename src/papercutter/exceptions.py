"""Custom exceptions for Papercutter."""



class PapercutterError(Exception):
    """Base exception for all Papercutter errors."""

    exit_code: int = 1
    default_hint: str | None = None

    def __init__(
        self,
        message: str,
        details: str | None = None,
        hint: str | None = None,
    ):
        self.message = message
        self.details = details
        self.hint = hint or self.default_hint
        super().__init__(message)


# Fetcher errors (10-19)
class FetchError(PapercutterError):
    """Error during paper fetching."""

    exit_code = 10


class PaperNotFoundError(FetchError):
    """Paper not found at source."""

    exit_code = 11
    default_hint = "Check the ID format (e.g., 2301.00001 for arXiv, 10.1234/... for DOI)"


class RateLimitError(FetchError):
    """Rate limited by source."""

    exit_code = 12
    default_hint = "Wait a few minutes and try again"


class NetworkError(FetchError):
    """Network connectivity issue."""

    exit_code = 13
    default_hint = "Check your internet connection"


# Extraction errors (20-29)
class ExtractionError(PapercutterError):
    """Error during content extraction."""

    exit_code = 20


class InvalidPDFError(ExtractionError):
    """PDF is corrupt or unreadable."""

    exit_code = 21
    default_hint = "Ensure the file is a valid PDF document"


class NoContentError(ExtractionError):
    """No extractable content found."""

    exit_code = 22
    default_hint = "The PDF may be scanned/image-only. OCR is not supported."


# Configuration errors (30-39)
class ConfigError(PapercutterError):
    """Configuration error."""

    exit_code = 30


class MissingAPIKeyError(ConfigError):
    """Required API key not configured."""

    exit_code = 31
    default_hint = "Set PAPERCUTTER_ANTHROPIC_API_KEY or configure in ~/.papercutter/config.yaml"


# LLM errors (40-49) - for v0.2
class LLMError(PapercutterError):
    """LLM processing error."""

    exit_code = 40


class LLMNotAvailableError(LLMError):
    """LLM not available or not configured."""

    exit_code = 41
    default_hint = "Set PAPERCUTTER_ANTHROPIC_API_KEY or install: pip install papercutter[llm]"


# Equation errors (50-59)
class EquationExtractionError(ExtractionError):
    """Error during equation extraction."""

    exit_code = 50
    default_hint = "Ensure PyMuPDF is installed: pip install pymupdf"


class EquationConversionError(PapercutterError):
    """Error during LaTeX conversion."""

    exit_code = 51
    default_hint = "Try a different conversion method: --method nougat|pix2tex|mathpix"


class MathPixAPIError(EquationConversionError):
    """MathPix API error."""

    exit_code = 52
    default_hint = "Check PAPERCUTTER_MATHPIX_APP_ID and PAPERCUTTER_MATHPIX_APP_KEY"
