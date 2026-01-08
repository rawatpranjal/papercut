"""Fetch commands for downloading papers from various sources."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()

app = typer.Typer(
    help="Download papers from various sources.",
    no_args_is_help=True,
)


@app.command()
def arxiv(
    paper_id: str = typer.Argument(..., help="arXiv paper ID (e.g., 2301.00001)"),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
):
    """Download paper from arXiv by ID."""
    from papercut.fetchers.arxiv import ArxivFetcher

    fetcher = ArxivFetcher()
    with console.status(f"Fetching arXiv:{paper_id}..."):
        doc = fetcher.fetch(paper_id, output)
    console.print(f"[green]Downloaded:[/green] {doc.path}")
    if doc.title:
        console.print(f"[dim]Title: {doc.title}[/dim]")


@app.command()
def doi(
    identifier: str = typer.Argument(..., help="DOI identifier (e.g., 10.1257/aer.20180779)"),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
):
    """Resolve DOI and download paper."""
    from papercut.fetchers.doi import DOIFetcher

    fetcher = DOIFetcher()
    with console.status(f"Resolving DOI:{identifier}..."):
        doc = fetcher.fetch(identifier, output)
    console.print(f"[green]Downloaded:[/green] {doc.path}")
    if doc.title:
        console.print(f"[dim]Title: {doc.title}[/dim]")


@app.command()
def ssrn(
    paper_id: str = typer.Argument(..., help="SSRN paper ID"),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
):
    """Download paper from SSRN."""
    from papercut.fetchers.ssrn import SSRNFetcher

    fetcher = SSRNFetcher()
    with console.status(f"Fetching SSRN:{paper_id}..."):
        doc = fetcher.fetch(paper_id, output)
    console.print(f"[green]Downloaded:[/green] {doc.path}")


@app.command()
def nber(
    paper_id: str = typer.Argument(..., help="NBER working paper ID (e.g., w29000)"),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
):
    """Download paper from NBER."""
    from papercut.fetchers.nber import NBERFetcher

    fetcher = NBERFetcher()
    with console.status(f"Fetching NBER:{paper_id}..."):
        doc = fetcher.fetch(paper_id, output)
    console.print(f"[green]Downloaded:[/green] {doc.path}")


@app.command()
def url(
    paper_url: str = typer.Argument(..., help="Direct URL to PDF"),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom filename (without extension).",
    ),
):
    """Download paper from direct URL."""
    from papercut.fetchers.url import URLFetcher

    fetcher = URLFetcher()
    with console.status(f"Downloading from URL..."):
        doc = fetcher.fetch(paper_url, output, name=name)
    console.print(f"[green]Downloaded:[/green] {doc.path}")
