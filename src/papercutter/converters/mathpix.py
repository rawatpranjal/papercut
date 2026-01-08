"""MathPix API-based equation converter (paid, high accuracy)."""

import base64

from papercutter.converters.base import BaseConverter
from papercutter.core.equations import LaTeXConversion
from papercutter.exceptions import MathPixAPIError


class MathPixConverter(BaseConverter):
    """Convert equations using MathPix API.

    MathPix provides high-accuracy (~95%) equation OCR via a paid API.

    Configuration:
        Set PAPERCUTTER_MATHPIX_APP_ID and PAPERCUTTER_MATHPIX_APP_KEY
        environment variables, or configure in ~/.papercutter/config.yaml
    """

    API_URL = "https://api.mathpix.com/v3/text"

    def __init__(self, app_id: str | None = None, app_key: str | None = None):
        """Initialize the MathPix converter.

        Args:
            app_id: MathPix app ID. If not provided, reads from settings.
            app_key: MathPix app key. If not provided, reads from settings.
        """
        self._app_id = app_id
        self._app_key = app_key
        self._available: bool | None = None

    def _get_credentials(self) -> tuple[str, str]:
        """Get MathPix credentials from args or settings.

        Returns:
            Tuple of (app_id, app_key).

        Raises:
            MathPixAPIError: If credentials are not configured.
        """
        app_id = self._app_id
        app_key = self._app_key

        if not app_id or not app_key:
            from papercutter.config.settings import get_settings

            settings = get_settings()
            app_id = app_id or settings.mathpix_app_id
            app_key = app_key or settings.mathpix_app_key

        if not app_id or not app_key:
            raise MathPixAPIError(
                "MathPix API credentials not configured",
                hint="Set PAPERCUTTER_MATHPIX_APP_ID and PAPERCUTTER_MATHPIX_APP_KEY",
            )

        return app_id, app_key

    def convert(self, image_data: bytes) -> LaTeXConversion:
        """Convert equation image to LaTeX using MathPix API.

        Args:
            image_data: PNG image bytes.

        Returns:
            LaTeXConversion with result.

        Raises:
            MathPixAPIError: If API call fails.
        """
        import httpx

        app_id, app_key = self._get_credentials()

        # Encode image as base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        headers = {
            "app_id": app_id,
            "app_key": app_key,
            "Content-Type": "application/json",
        }

        payload = {
            "src": f"data:image/png;base64,{image_b64}",
            "formats": ["latex_styled"],
            "data_options": {
                "include_asciimath": False,
                "include_latex": True,
            },
        }

        try:
            response = httpx.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise MathPixAPIError(
                    "MathPix API authentication failed",
                    details=str(e),
                    hint="Check your PAPERCUTTER_MATHPIX_APP_ID and PAPERCUTTER_MATHPIX_APP_KEY",
                ) from None
            elif e.response.status_code == 429:
                raise MathPixAPIError(
                    "MathPix API rate limit exceeded",
                    details=str(e),
                    hint="Wait a moment and try again, or check your usage quota",
                ) from None
            else:
                raise MathPixAPIError(
                    f"MathPix API error: {e.response.status_code}",
                    details=str(e),
                ) from None
        except httpx.RequestError as e:
            raise MathPixAPIError(
                "MathPix API request failed",
                details=str(e),
                hint="Check your internet connection",
            ) from None

        result = response.json()

        # Extract LaTeX from response
        latex = result.get("latex_styled", "") or result.get("latex", "")

        # MathPix provides a confidence score
        confidence = result.get("confidence", 0.95)

        # Handle errors in response
        if result.get("error"):
            raise MathPixAPIError(
                f"MathPix conversion error: {result['error']}",
                details=result.get("error_info", {}).get("message", ""),
            )

        return LaTeXConversion(
            latex=latex,
            confidence=confidence,
            method="mathpix",
        )

    def is_available(self) -> bool:
        """Check if MathPix is available (credentials configured)."""
        if self._available is None:
            try:
                self._get_credentials()
                self._available = True
            except MathPixAPIError:
                self._available = False
        return self._available

    @property
    def name(self) -> str:
        """Return converter name."""
        return "mathpix"
