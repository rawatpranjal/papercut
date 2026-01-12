"""The Razor Pipeline - 4 commands for PDF to Data extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(
    name="papercutter",
    help="Extract structured data from academic papers.",
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
def configure(
    prompt: Annotated[
        str | None,
        typer.Option("--prompt", "-p", help="Custom prompt for schema generation")
    ] = None,
) -> None:
    """Generate extraction schema from paper abstracts."""
    from papercutter.extract import generate_schema

    generate_schema(custom_prompt=prompt)


@app.command()
def extract() -> None:
    """Extract data fields from papers using LLM."""
    from papercutter.extract import run_extraction

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


# --- Book Subcommands ---


book_app = typer.Typer(
    name="book",
    help="Process book-length PDFs: detect chapters, summarize, synthesize.",
    no_args_is_help=True,
)


@book_app.command("index")
def book_index(
    pdf_path: Annotated[Path, typer.Argument(help="Path to book PDF")],
) -> None:
    """Detect chapter boundaries in a book PDF."""
    from papercutter.book import run_book_index

    if not pdf_path.exists():
        console.print(f"[red]Error:[/red] PDF not found: {pdf_path}")
        raise typer.Exit(1)

    run_book_index(pdf_path)


@book_app.command("extract")
def book_extract(
    docling: Annotated[
        bool,
        typer.Option("--docling", "-d", help="Use Docling for rich markdown extraction")
    ] = False,
) -> None:
    """Extract chapter text from indexed book."""
    from papercutter.book import run_book_extract

    run_book_extract(use_docling=docling)


@book_app.command("summarize")
def book_summarize() -> None:
    """Summarize each chapter with LLM."""
    from papercutter.book import run_book_summarize

    run_book_summarize()


@book_app.command("report")
def book_report() -> None:
    """Generate book summary PDF (1 page per chapter)."""
    from papercutter.book import run_book_report

    run_book_report()


app.add_typer(book_app, name="book")


if __name__ == "__main__":
    app()
