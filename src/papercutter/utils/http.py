"""HTTP utilities for fetching papers."""

from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

import certifi
import httpx

from papercutter.exceptions import NetworkError, RateLimitError

# Default timeout for HTTP requests (in seconds)
DEFAULT_TIMEOUT = 30.0

# Default headers to mimic a real browser (helps avoid bot detection)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
"""Default HTTP headers used for outbound requests."""

# User-friendly HTTP error messages
HTTP_ERROR_MESSAGES = {
    400: "Bad request - the server couldn't understand the request",
    401: "Authentication required - login credentials needed",
    403: "Access denied - the server blocked this request",
    404: "Resource not found - the page or file doesn't exist",
    429: "Rate limited - please wait before making more requests",
    500: "Server error - the server encountered an internal problem",
    502: "Bad gateway - the server received an invalid response",
    503: "Service unavailable - the server is temporarily overloaded",
    504: "Gateway timeout - the server took too long to respond",
}


def get_friendly_error_message(status_code: int) -> str:
    """Get a user-friendly error message for an HTTP status code.

    Args:
        status_code: HTTP status code.

    Returns:
        User-friendly error message.
    """
    return HTTP_ERROR_MESSAGES.get(status_code, f"HTTP error {status_code}")


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
        verify=certifi.where(),
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


def download_file_with_progress(
    url: str,
    output_path: Path,
    filename: Optional[str] = None,
    client: Optional[httpx.Client] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Download a file from URL with progress tracking.

    Uses streaming to report download progress.

    Args:
        url: URL to download from.
        output_path: Directory or file path to save to.
        filename: Optional filename override.
        client: Optional httpx client to reuse.
        progress_callback: Optional callback(downloaded_bytes, total_bytes).
            Called periodically during download. total_bytes may be 0 if
            Content-Length header is not present.

    Returns:
        Path to the downloaded file.

    Raises:
        NetworkError: If download fails.
        RateLimitError: If rate limited.
    """
    should_close = client is None
    client = client or get_client()

    try:
        # Use streaming request for progress tracking
        with client.stream("GET", url) as response:
            if response.status_code == 429:
                raise RateLimitError(
                    "Rate limited by server",
                    details=f"URL: {url}",
                )

            response.raise_for_status()

            # Get total size from headers (may be 0 if not present)
            total_size = int(response.headers.get("content-length", 0))

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

            # Stream to file with progress
            downloaded = 0
            with open(file_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

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


# Async HTTP utilities for concurrent downloads

ASYNC_TIMEOUT = 60.0


def get_async_client(**kwargs) -> httpx.AsyncClient:
    """Get a configured async HTTP client.

    Args:
        **kwargs: Additional arguments to pass to httpx.AsyncClient.

    Returns:
        Configured httpx.AsyncClient instance.
    """
    return httpx.AsyncClient(
        timeout=kwargs.pop("timeout", ASYNC_TIMEOUT),
        headers={**DEFAULT_HEADERS, **kwargs.pop("headers", {})},
        follow_redirects=True,
        verify=certifi.where(),
        **kwargs,
    )


async def download_file_async(
    url: str,
    output_path: Path,
    filename: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Path:
    """Download a file from URL asynchronously.

    Args:
        url: URL to download from.
        output_path: Directory or file path to save to.
        filename: Optional filename override.
        client: Optional async httpx client to reuse.

    Returns:
        Path to the downloaded file.

    Raises:
        NetworkError: If download fails.
        RateLimitError: If rate limited.
    """
    should_close = client is None
    client = client or get_async_client()

    try:
        async with client.stream("GET", url) as response:
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

            # Stream to file
            with open(file_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

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
            await client.aclose()


async def download_files_batch(
    urls: list[str],
    output_dir: Path,
    max_concurrent: int = 5,
) -> list[tuple[str, Path | Exception]]:
    """Download multiple files concurrently.

    Args:
        urls: List of URLs to download.
        output_dir: Directory to save downloaded files.
        max_concurrent: Maximum number of concurrent downloads.

    Returns:
        List of (url, result) tuples where result is either Path or Exception.
    """
    import asyncio

    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[tuple[str, Path | Exception]] = []

    async def download_with_semaphore(url: str) -> tuple[str, Path | Exception]:
        async with semaphore:
            try:
                path = await download_file_async(url, output_dir)
                return (url, path)
            except Exception as e:
                return (url, e)

    async with get_async_client() as client:
        tasks = [download_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)

    return results
