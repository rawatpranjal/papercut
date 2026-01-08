"""Fetch commands for downloading papers from various sources."""

from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console

from papercutter.cli.utils import handle_errors, is_quiet
from papercutter.fetchers.base import Document

app = typer.Typer(
    help="Download papers from various sources.",
    no_args_is_help=True,
)


def _get_console() -> Console:
    """Get a console for output messages (respects quiet mode for status only)."""
    return Console()


def _read_batch_file(batch_file: Path) -> list[tuple[int, str]]:
    """Read identifiers from a batch file."""
    console = _get_console()
    if not batch_file.exists():
        console.print(f"[red]Error:[/red] Batch file not found: {batch_file}")
        raise typer.Exit(1)

    identifiers: list[tuple[int, str]] = []
    with open(batch_file, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            identifiers.append((line_no, value))
    return identifiers


def _run_fetch_batch(
    batch_file: Path,
    source_name: str,
    fetch_func: Callable[[str], Document],
    metadata: bool,
) -> None:
    """Execute batch fetching for a specific source."""
    identifiers = _read_batch_file(batch_file)
    console = _get_console()
    quiet_mode = is_quiet()

    if not identifiers:
        if not quiet_mode:
            console.print(f"[yellow]No identifiers found in {batch_file}[/yellow]")
        raise typer.Exit(0)

    if not quiet_mode:
        console.print(
            f"[bold]{source_name.title()} batch:[/bold] {len(identifiers)} item(s) from {batch_file}"
        )

    successes = 0
    failures: list[tuple[int, str, str]] = []

    for idx, identifier in identifiers:
        try:
            doc = fetch_func(identifier)
            successes += 1
            if metadata:
                doc.save_metadata()
            if not quiet_mode:
                console.print(f"  [green]Downloaded:[/green] {doc.path.name}")
        except Exception as e:
            failures.append((idx, identifier, str(e)))
            if not quiet_mode:
                console.print(f"  [red]Failed line {idx}:[/red] {e}")

    if not quiet_mode:
        console.print(
            f"[bold]Done:[/bold] [green]{successes} success[/green], "
            f"[red]{len(failures)} failed[/red]"
        )

    if failures:
        raise typer.Exit(1)


@app.command()
@handle_errors
def arxiv(
    paper_id: str | None = typer.Argument(None, help="arXiv paper ID (e.g., 2301.00001)"),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        help="File with arXiv IDs (one per line). Ignores single argument when provided.",
    ),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
    metadata: bool = typer.Option(
        False,
        "--metadata",
        "-m",
        help="Save metadata as JSON sidecar file (.meta.json).",
    ),
):
    """Download paper from arXiv by ID."""
    from papercutter.fetchers.arxiv import ArxivFetcher

    console = _get_console()
    fetcher = ArxivFetcher()

    if batch:
        _run_fetch_batch(
            batch,
            "arxiv",
            lambda identifier: fetcher.fetch(identifier, output),
            metadata,
        )
        return

    if not paper_id:
        raise typer.BadParameter("paper_id is required unless --batch is provided")

    if is_quiet():
        doc = fetcher.fetch(paper_id, output)
    else:
        with console.status(f"Fetching arXiv:{paper_id}..."):
            doc = fetcher.fetch(paper_id, output)
        console.print(f"[green]Downloaded:[/green] {doc.path}")
        if doc.title:
            console.print(f"[dim]Title: {doc.title}[/dim]")

    if metadata:
        meta_path = doc.save_metadata()
        if not is_quiet():
            console.print(f"[dim]Metadata: {meta_path}[/dim]")


@app.command()
@handle_errors
def doi(
    identifier: str | None = typer.Argument(
        None, help="DOI identifier (e.g., 10.1257/aer.20180779)"
    ),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        help="File with DOIs (one per line). Ignores single identifier when provided.",
    ),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
    metadata: bool = typer.Option(
        False,
        "--metadata",
        "-m",
        help="Save metadata as JSON sidecar file (.meta.json).",
    ),
):
    """Resolve DOI and download paper."""
    from papercutter.fetchers.doi import DOIFetcher

    console = _get_console()
    fetcher = DOIFetcher()

    if batch:
        _run_fetch_batch(
            batch,
            "doi",
            lambda ident: fetcher.fetch(ident, output),
            metadata,
        )
        return

    if not identifier:
        raise typer.BadParameter("identifier is required unless --batch is provided")

    if is_quiet():
        doc = fetcher.fetch(identifier, output)
    else:
        with console.status(f"Resolving DOI:{identifier}..."):
            doc = fetcher.fetch(identifier, output)
        console.print(f"[green]Downloaded:[/green] {doc.path}")
        if doc.title:
            console.print(f"[dim]Title: {doc.title}[/dim]")

    if metadata:
        meta_path = doc.save_metadata()
        if not is_quiet():
            console.print(f"[dim]Metadata: {meta_path}[/dim]")


@app.command()
@handle_errors
def ssrn(
    paper_id: str | None = typer.Argument(None, help="SSRN paper ID"),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        help="File with SSRN IDs (one per line). Ignores single argument when provided.",
    ),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
    metadata: bool = typer.Option(
        False,
        "--metadata",
        "-m",
        help="Save metadata as JSON sidecar file (.meta.json).",
    ),
):
    """Download paper from SSRN."""
    from papercutter.fetchers.ssrn import SSRNFetcher

    console = _get_console()
    fetcher = SSRNFetcher()

    if batch:
        _run_fetch_batch(
            batch,
            "ssrn",
            lambda identifier: fetcher.fetch(identifier, output),
            metadata,
        )
        return

    if not paper_id:
        raise typer.BadParameter("paper_id is required unless --batch is provided")

    if is_quiet():
        doc = fetcher.fetch(paper_id, output)
    else:
        with console.status(f"Fetching SSRN:{paper_id}..."):
            doc = fetcher.fetch(paper_id, output)
        console.print(f"[green]Downloaded:[/green] {doc.path}")

    if metadata:
        meta_path = doc.save_metadata()
        if not is_quiet():
            console.print(f"[dim]Metadata: {meta_path}[/dim]")


@app.command()
@handle_errors
def nber(
    paper_id: str | None = typer.Argument(None, help="NBER working paper ID (e.g., w29000)"),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        help="File with NBER IDs (one per line). Ignores single argument when provided.",
    ),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
    metadata: bool = typer.Option(
        False,
        "--metadata",
        "-m",
        help="Save metadata as JSON sidecar file (.meta.json).",
    ),
):
    """Download paper from NBER."""
    from papercutter.fetchers.nber import NBERFetcher

    console = _get_console()
    fetcher = NBERFetcher()

    if batch:
        _run_fetch_batch(
            batch,
            "nber",
            lambda identifier: fetcher.fetch(identifier, output),
            metadata,
        )
        return

    if not paper_id:
        raise typer.BadParameter("paper_id is required unless --batch is provided")

    if is_quiet():
        doc = fetcher.fetch(paper_id, output)
    else:
        with console.status(f"Fetching NBER:{paper_id}..."):
            doc = fetcher.fetch(paper_id, output)
        console.print(f"[green]Downloaded:[/green] {doc.path}")

    if metadata:
        meta_path = doc.save_metadata()
        if not is_quiet():
            console.print(f"[dim]Metadata: {meta_path}[/dim]")


@app.command()
@handle_errors
def url(
    paper_url: str | None = typer.Argument(None, help="Direct URL to PDF"),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF.",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom filename (without extension).",
    ),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        help="File with direct PDF URLs (one per line). Ignores single argument when provided.",
    ),
    metadata: bool = typer.Option(
        False,
        "--metadata",
        "-m",
        help="Save metadata as JSON sidecar file (.meta.json).",
    ),
):
    """Download paper from direct URL."""
    from papercutter.fetchers.url import URLFetcher

    console = _get_console()
    fetcher = URLFetcher()

    if batch:
        _run_fetch_batch(
            batch,
            "url",
            lambda identifier: fetcher.fetch(identifier, output),
            metadata,
        )
        return

    if not paper_url:
        raise typer.BadParameter("paper_url is required unless --batch is provided")

    if is_quiet():
        doc = fetcher.fetch(paper_url, output, name=name)
    else:
        with console.status("Downloading from URL..."):
            doc = fetcher.fetch(paper_url, output, name=name)
        console.print(f"[green]Downloaded:[/green] {doc.path}")

    if metadata:
        meta_path = doc.save_metadata()
        if not is_quiet():
            console.print(f"[dim]Metadata: {meta_path}[/dim]")


@app.command()
@handle_errors
def batch(
    file_path: Path = typer.Argument(..., help="File with paper identifiers (one per line)"),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDFs.",
    ),
    parallel: bool = typer.Option(
        False,
        "--parallel",
        "-p",
        help="Use async parallel downloads (faster, but no progress per file).",
    ),
    max_concurrent: int = typer.Option(
        5,
        "--max-concurrent",
        help="Maximum concurrent downloads when using --parallel.",
    ),
    continue_on_error: bool = typer.Option(
        True,
        "--continue-on-error/--stop-on-error",
        help="Continue after download failures.",
    ),
    delay: float = typer.Option(
        1.0,
        "--delay",
        "-d",
        help="Delay between downloads in seconds (ignored with --parallel).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be downloaded without fetching.",
    ),
    metadata: bool = typer.Option(
        False,
        "--metadata",
        "-m",
        help="Save metadata as JSON sidecar files (.meta.json).",
    ),
):
    """Download multiple papers from a list file.

    The file should contain one identifier per line. Supported formats:

    \b
        arxiv:1706.03762
        doi:10.1257/aer.20180779
        ssrn:1234567
        nber:w29000
        https://example.com/paper.pdf

    Lines starting with # are treated as comments.

    Examples:

    \b
        papercutter fetch batch papers.txt -o ./library/
        papercutter fetch batch papers.txt --dry-run
        papercutter fetch batch papers.txt --delay 2.0 --stop-on-error
        papercutter fetch batch papers.txt --metadata
    """
    import time

    from papercutter.api import fetch_paper, fetch_paper_async
    from papercutter.output import get_formatter

    console = _get_console()
    formatter = get_formatter(quiet=is_quiet())
    quiet_mode = is_quiet()

    # Read and parse the file
    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(1)

    identifiers = []
    with open(file_path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            identifiers.append((line_no, line))

    if not identifiers:
        console.print("[yellow]No paper identifiers found in file[/yellow]")
        raise typer.Exit(0)

    if not quiet_mode:
        console.print(f"[bold]Found {len(identifiers)} paper(s) to fetch[/bold]")

    # Dry run mode
    if dry_run:
        result = {
            "dry_run": True,
            "file": str(file_path),
            "count": len(identifiers),
            "identifiers": [{"line": ln, "id": ident} for ln, ident in identifiers],
        }
        if formatter.use_json:
            formatter.output(result)
        else:
            console.print("\n[dim]Would download:[/dim]")
            for ln, ident in identifiers:
                console.print(f"  Line {ln}: {ident}")
        return

    # Download papers
    output.mkdir(parents=True, exist_ok=True)
    downloaded = []
    failed = []

    if parallel:
        # Parallel async downloads
        import asyncio

        async def fetch_all_parallel():
            semaphore = asyncio.Semaphore(max_concurrent)

            async def fetch_one(line_no: int, identifier: str):
                async with semaphore:
                    try:
                        doc = await fetch_paper_async(identifier, output)
                        if metadata:
                            doc.save_metadata()
                        return (line_no, identifier, doc, None)
                    except Exception as e:
                        return (line_no, identifier, None, str(e)[:100])

            tasks = [fetch_one(ln, ident) for ln, ident in identifiers]
            return await asyncio.gather(*tasks)

        if not quiet_mode:
            with console.status(f"Downloading {len(identifiers)} papers in parallel..."):
                results = asyncio.run(fetch_all_parallel())
        else:
            results = asyncio.run(fetch_all_parallel())

        for line_no, identifier, doc, error in results:
            if doc:
                downloaded.append({"line": line_no, "id": identifier, "path": str(doc.path.name)})
            else:
                failed.append({"line": line_no, "id": identifier, "error": error})

        if not quiet_mode:
            for item in downloaded:
                console.print(f"  [green]Downloaded:[/green] {item['path']}")
            for item in failed:
                console.print(f"  [red]Failed:[/red] {item['id']} - {item['error']}")

    else:
        # Sequential downloads with delay
        for i, (line_no, identifier) in enumerate(identifiers):
            if not quiet_mode:
                console.print(f"\n[dim][{i + 1}/{len(identifiers)}] Fetching: {identifier}[/dim]")

            try:
                doc = fetch_paper(identifier, output)
                downloaded.append({"line": line_no, "id": identifier, "path": str(doc.path.name)})
                if not quiet_mode:
                    console.print(f"  [green]Downloaded:[/green] {doc.path.name}")
                if metadata:
                    doc.save_metadata()
            except Exception as e:
                failed.append({"line": line_no, "id": identifier, "error": str(e)[:100]})
                if not quiet_mode:
                    console.print(f"  [red]Failed:[/red] {e}")
                if not continue_on_error:
                    break

            # Rate limiting between downloads
            if i < len(identifiers) - 1 and delay > 0:
                time.sleep(delay)

    # Summary
    if not quiet_mode:
        console.print("\n[bold]Done:[/bold]")
        console.print(f"  [green]{len(downloaded)} downloaded[/green]")
        if failed:
            console.print(f"  [red]{len(failed)} failed[/red]")

    # JSON output
    result = {
        "success": len(failed) == 0 or continue_on_error,
        "file": str(file_path),
        "output_dir": str(output),
        "downloaded": len(downloaded),
        "failed": len(failed),
        "downloaded_files": downloaded,
    }
    if failed:
        result["failed_items"] = failed

    if formatter.use_json:
        formatter.output(result)
