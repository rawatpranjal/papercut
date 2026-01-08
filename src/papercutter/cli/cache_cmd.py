"""Cache management commands."""

import json
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def clear_cache(
    pdf_path: Path | None = typer.Argument(
        None,
        help="PDF file to clear cache for (omit to clear all)",
    ),
):
    """Clear cached extraction data.

    Clear cache for a specific file or all cached data.

    Examples:

        papercutter clear-cache

        papercutter clear-cache paper.pdf
    """
    from papercutter.cache import get_cache

    cache = get_cache()

    if pdf_path:
        if not pdf_path.exists():
            console.print(f"[red]File not found:[/red] {pdf_path}")
            raise typer.Exit(1)

        cache_info = cache.cache_info(pdf_path)
        if cache_info["cached"]:
            cache.clear(pdf_path)
            result = {
                "success": True,
                "cleared": str(pdf_path),
                "cache_path": cache_info["cache_path"],
            }
        else:
            result = {
                "success": True,
                "cleared": None,
                "message": f"No cache found for {pdf_path}",
            }
    else:
        cache.clear()
        result = {
            "success": True,
            "cleared": "all",
            "cache_dir": str(cache.cache_dir),
        }

    console.print(json.dumps(result, indent=2))


def cache_info(
    pdf_path: Path = typer.Argument(..., help="PDF file to check cache for"),
):
    """Show cache info for a PDF file.

    Example:

        papercutter cache-info paper.pdf
    """
    from papercutter.cache import get_cache

    cache = get_cache()

    if not pdf_path.exists():
        console.print(f"[red]File not found:[/red] {pdf_path}")
        raise typer.Exit(1)

    info = cache.cache_info(pdf_path)
    info["file"] = str(pdf_path.name)

    console.print(json.dumps(info, indent=2))
