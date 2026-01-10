"""The Razor Pipeline - 4 commands for PDF to Data extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(
    name="papercutter",
    help="PDF to Data Factory: Extract structured data from academic papers.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def ingest(
    source: Annotated[Path, typer.Argument(help="Directory containing PDF files")],
) -> None:
    """Digitize PDFs with Docling (PDF -> Markdown + Tables)."""
    from papercutter.ingest import run_ingest

    if not source.exists():
        console.print(f"[red]Error:[/red] Source path does not exist: {source}")
        raise typer.Exit(1)

    if not source.is_dir():
        console.print(f"[red]Error:[/red] Source must be a directory: {source}")
        raise typer.Exit(1)

    run_ingest(source)


@app.command()
def configure() -> None:
    """Generate extraction schema from paper abstracts."""
    from papercutter.grind import generate_schema

    generate_schema()


@app.command()
def grind() -> None:
    """Extract data fields and write summaries using LLM."""
    from papercutter.grind import run_extraction

    run_extraction()


@app.command()
def report(
    condensed: Annotated[
        bool,
        typer.Option("--condensed", "-c", help="Generate condensed table for appendix")
    ] = False,
) -> None:
    """Generate matrix.csv and review.pdf from extractions."""
    from papercutter.report import build_report, build_condensed

    if condensed:
        build_condensed()
    else:
        build_report()


if __name__ == "__main__":
    app()
