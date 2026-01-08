"""Custom exceptions for Papercut."""

from typing import Optional


class PapercutError(Exception):
    """Base exception for all Papercut errors."""

    exit_code: int = 1

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


# Fetcher errors (10-19)
class FetchError(PapercutError):
    """Error during paper fetching."""

    exit_code = 10


class PaperNotFoundError(FetchError):
    """Paper not found at source."""

    exit_code = 11


class RateLimitError(FetchError):
    """Rate limited by source."""

    exit_code = 12


class NetworkError(FetchError):
    """Network connectivity issue."""

    exit_code = 13


# Extraction errors (20-29)
class ExtractionError(PapercutError):
    """Error during content extraction."""

    exit_code = 20


class InvalidPDFError(ExtractionError):
    """PDF is corrupt or unreadable."""

    exit_code = 21


class NoContentError(ExtractionError):
    """No extractable content found."""

    exit_code = 22


# Configuration errors (30-39)
class ConfigError(PapercutError):
    """Configuration error."""

    exit_code = 30


class MissingAPIKeyError(ConfigError):
    """Required API key not configured."""

    exit_code = 31


# LLM errors (40-49) - for v0.2
class LLMError(PapercutError):
    """LLM processing error."""

    exit_code = 40
