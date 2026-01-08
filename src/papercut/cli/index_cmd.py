"""Index command for building document maps."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from papercut.output import get_formatter

console = Console()


def index(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    doc_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Document type: paper or book (auto-detected if not specified)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force re-indexing even if cached",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout)",
    ),
    use_json: bool = typer.Option(
        False,
        "--json",
        help="Force JSON output",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Force pretty output",
    ),
):
    """Build a structural map of a PDF document.

    Detects sections, tables, figures, and references.
    Returns JSON suitable for LLM processing.

    Examples:

        papercut index paper.pdf

        papercut index book.pdf --type book

        papercut index paper.pdf -o index.json
    """
    from papercut.index import DocumentIndexer

    # Validate type
    if doc_type and doc_type not in ("paper", "book"):
        console.print(f"[red]Invalid type:[/red] {doc_type}")
        console.print("[dim]Valid types: paper, book[/dim]")
        raise typer.Exit(1)

    indexer = DocumentIndexer()
    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)

    try:
        doc_index = indexer.index(
            pdf_path=pdf_path,
            doc_type=doc_type,
            force=force,
        )

        result = doc_index.to_dict()

        # Add success/cached metadata
        output_data = {
            "success": True,
            "cached": not force and indexer.cache.has_index(pdf_path),
            **result,
        }

        if output:
            json_output = json.dumps(output_data, indent=2)
            output.write_text(json_output)
            console.print(f"[green]Saved:[/green] {output}")
        else:
            formatter.output(output_data)

    except FileNotFoundError:
        console.print(f"[red]File not found:[/red] {pdf_path}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def chapters(
    pdf_path: Path = typer.Argument(..., help="Path to book PDF"),
    use_json: bool = typer.Option(
        False,
        "--json",
        help="Force JSON output",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Force pretty output",
    ),
):
    """List detected chapters in a book PDF.

    Uses PDF bookmarks/outline if available, otherwise
    falls back to text pattern detection.

    Example:

        papercut chapters textbook.pdf
    """
    from papercut.books.splitter import ChapterSplitter

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)
    splitter = ChapterSplitter()
    detected = splitter.detect_chapters(pdf_path)

    if not detected:
        result = {"success": True, "file": str(pdf_path.name), "chapters": [], "count": 0}
    else:
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "count": len(detected),
            "chapters": [
                {
                    "id": i + 1,
                    "title": ch.title,
                    "pages": [ch.start_page + 1, ch.end_page],
                    "page_count": ch.page_count,
                }
                for i, ch in enumerate(detected)
            ],
        }

    formatter.output(result)


def info(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    use_json: bool = typer.Option(
        False,
        "--json",
        help="Force JSON output",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Force pretty output",
    ),
):
    """Quick metadata about a PDF (no indexing).

    Returns basic info like page count without building full index.

    Example:

        papercut info paper.pdf
    """
    from pypdf import PdfReader

    from papercut.cache import file_hash

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)

    try:
        reader = PdfReader(pdf_path)

        result = {
            "success": True,
            "file": str(pdf_path.name),
            "pages": len(reader.pages),
            "hash": file_hash(pdf_path),
        }

        if reader.metadata:
            result["metadata"] = {}
            if reader.metadata.title:
                result["metadata"]["title"] = reader.metadata.title
            if reader.metadata.author:
                result["metadata"]["author"] = reader.metadata.author
            if reader.metadata.subject:
                result["metadata"]["subject"] = reader.metadata.subject

        formatter.output(result)

    except FileNotFoundError:
        console.print(f"[red]File not found:[/red] {pdf_path}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
