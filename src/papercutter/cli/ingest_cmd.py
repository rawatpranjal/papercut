"""Ingest command for Papercutter Factory.

Handles the full ingestion pipeline:
1. Sawmill: Split large PDFs
2. Matching: Align PDFs with BibTeX
3. Digitize: Convert PDFs to Markdown
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from papercutter.ingest import IngestPipeline, IngestProgress
from papercutter.project.manager import ProjectManager

console = Console()


def _progress_callback(progress: IngestProgress) -> None:
    """Display progress updates."""
    msg = f"[{progress.stage}] {progress.current}/{progress.total}: {progress.message}"
    console.print(f"  {msg}", highlight=False)


def ingest(
    source: Annotated[
        Path | None,
        typer.Argument(help="PDF file or directory to ingest."),
    ] = None,
    bib: Path | None = typer.Option(
        None,
        "--bib",
        "-b",
        help="BibTeX file for matching (overrides project config).",
        exists=True,
        dir_okay=False,
    ),
    no_split: bool = typer.Option(
        False,
        "--no-split",
        help="Skip automatic splitting of large books.",
    ),
    no_fetch: bool = typer.Option(
        False,
        "--no-fetch",
        help="Don't fetch missing papers from DOI/arXiv.",
    ),
    directory: Path = typer.Option(
        Path("."),
        "--dir",
        "-d",
        help="Project directory.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed progress.",
    ),
):
    """Ingest PDFs into the project.

    This command runs the full ingestion pipeline:

    1. **Sawmill**: Detect and split large PDFs (500+ pages) into chapters
    2. **Matching**: Align PDFs with BibTeX entries (if provided)
    3. **Fetching**: Download papers for BibTeX entries without PDFs
    4. **Conversion**: Convert PDFs to Markdown (Docling with OCR fallback)

    Examples:
        papercutter ingest papers/              # Ingest directory
        papercutter ingest paper.pdf            # Ingest single file
        papercutter ingest --bib refs.bib       # With BibTeX matching
    """
    directory = Path(directory).resolve()
    manager = ProjectManager(directory)

    # Check if project exists
    if not manager.exists():
        console.print("[red]No project found. Run 'papercutter init' first.[/red]")
        raise typer.Exit(1)

    # Load project
    manager.load()

    # Determine source
    if source is None:
        # Look for PDFs in project directory
        pdf_files = list(directory.glob("*.pdf"))
        if not pdf_files:
            console.print("[yellow]No PDF files found in current directory.[/yellow]")
            console.print("Specify a source: papercutter ingest <path>")
            raise typer.Exit(1)
    else:
        source = Path(source).resolve()
        if source.is_file():
            pdf_files = [source]
        elif source.is_dir():
            pdf_files = list(source.glob("**/*.pdf"))
        else:
            console.print(f"[red]Source not found: {source}[/red]")
            raise typer.Exit(1)

    if not pdf_files:
        console.print("[yellow]No PDF files found.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold]Found {len(pdf_files)} PDF(s) to ingest[/bold]")

    # Get BibTeX file
    bib_file = bib or (
        Path(manager.config.bibtex_path) if manager.config.bibtex_path else None
    )
    if bib_file:
        console.print(f"  BibTeX: {bib_file}")

    # Configure pipeline
    split_threshold = 99999 if no_split else manager.config.split_threshold_pages

    pipeline = IngestPipeline(
        split_threshold=split_threshold,
        docling_enabled=True,
        fetch_missing=not no_fetch,
        progress_callback=_progress_callback if verbose else None,
    )

    # Run ingestion
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Ingesting papers...", total=None)

        result = pipeline.ingest(
            pdf_files=pdf_files,
            bib_file=bib_file,
            output_dir=manager.project_dir,
        )

        progress.update(task, completed=True)

    # Update inventory
    for entry in result.entries:
        manager.inventory.add_paper(entry)
    manager.save()

    # Report results
    console.print()
    console.print("[bold]Ingestion complete:[/bold]")
    console.print(f"  Papers processed: {len(result.entries)}")

    if result.split_results:
        split_count = sum(1 for r in result.split_results if r.was_split)
        if split_count:
            console.print(f"  Books split: {split_count}")

    if result.match_result:
        console.print(f"  Matched to BibTeX: {len(result.match_result.matched)}")
        if result.match_result.bib_only:
            console.print(f"  BibTeX-only (fetched): {len(result.fetched_papers)}")
        if result.match_result.pdf_only:
            console.print(f"  PDF-only (generated): {len(result.match_result.pdf_only)}")

    if result.errors:
        console.print(f"  [yellow]Errors: {len(result.errors)}[/yellow]")
        if verbose:
            for ctx, msg in result.errors:
                console.print(f"    [dim]{ctx}: {msg}[/dim]")

    console.print()
    console.print("Next: Run [bold]papercutter configure[/bold] to set up extraction schema")
