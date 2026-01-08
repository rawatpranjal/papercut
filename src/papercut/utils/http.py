"""HTTP utilities for fetching papers."""

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from papercut.exceptions import NetworkError, RateLimitError

# Default timeout for HTTP requests (in seconds)
DEFAULT_TIMEOUT = 30.0

# Default headers to mimic a browser
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Papercut/0.1; +https://github.com/pranjalrawat007/papercut)"
}


def get_client(**kwargs) -> httpx.Client:
    """Get a configured HTTP client.

    Args:
        **kwargs: Additional arguments to pass to httpx.Client.

    Returns:
        Configured httpx.Client instance.
    """
    return httpx.Client(
        timeout=kwargs.pop("timeout", DEFAULT_TIMEOUT),
        headers={**DEFAULT_HEADERS, **kwargs.pop("headers", {})},
        follow_redirects=True,
        **kwargs,
    )


def download_file(
    url: str,
    output_path: Path,
    filename: Optional[str] = None,
    client: Optional[httpx.Client] = None,
) -> Path:
    """Download a file from URL.

    Args:
        url: URL to download from.
        output_path: Directory or file path to save to.
        filename: Optional filename override.
        client: Optional httpx client to reuse.

    Returns:
        Path to the downloaded file.

    Raises:
        NetworkError: If download fails.
        RateLimitError: If rate limited.
    """
    should_close = client is None
    client = client or get_client()

    try:
        response = client.get(url)

        if response.status_code == 429:
            raise RateLimitError(
                "Rate limited by server",
                details=f"URL: {url}",
            )

        response.raise_for_status()

        # Determine output file path
        if output_path.is_dir():
            if filename:
                file_path = output_path / filename
            else:
                # Try to get filename from URL
                parsed = urlparse(url)
                url_filename = Path(parsed.path).name
                if url_filename and "." in url_filename:
                    file_path = output_path / url_filename
                else:
                    file_path = output_path / "download.pdf"
        else:
            file_path = output_path

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        file_path.write_bytes(response.content)
        return file_path

    except httpx.HTTPStatusError as e:
        raise NetworkError(
            f"HTTP error {e.response.status_code}",
            details=f"URL: {url}",
        ) from e
    except httpx.RequestError as e:
        raise NetworkError(
            f"Request failed: {e}",
            details=f"URL: {url}",
        ) from e
    finally:
        if should_close:
            client.close()
