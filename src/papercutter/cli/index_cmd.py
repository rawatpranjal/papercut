"""Index command for building document maps."""

import json
from pathlib import Path

import typer
from rich.console import Console

from papercutter.output import get_formatter

console = Console()


def index(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    doc_type: str | None = typer.Option(
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
    output: Path | None = typer.Option(
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

        papercutter index paper.pdf

        papercutter index book.pdf --type book

        papercutter index paper.pdf -o index.json
    """
    from papercutter.index import DocumentIndexer

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

        papercutter chapters textbook.pdf
    """
    from papercutter.books.splitter import ChapterSplitter

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
    wpm: int = typer.Option(
        250,
        "--wpm",
        help="Words per minute for reading time estimate",
    ),
    quick: bool = typer.Option(
        False,
        "--quick",
        "-q",
        help="Quick mode: basic info without full indexing",
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
    """Get comprehensive statistics about a PDF.

    Shows page count, word count, figures, tables, references,
    sections with word counts, and estimated reading time.

    Use --quick for basic info without full text extraction.

    Examples:

        papercutter info paper.pdf

        papercutter info paper.pdf --wpm 300

        papercutter info paper.pdf --quick
    """
    from pypdf import PdfReader

    from papercutter.cache import file_hash

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)

    try:
        if quick:
            # Quick mode: basic info only (original behavior)
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
            return

        # Full info mode: comprehensive statistics
        from papercutter.core.text import TextExtractor
        from papercutter.extractors.pdfplumber import PdfPlumberExtractor
        from papercutter.index import DocumentIndexer

        # Get document index
        indexer = DocumentIndexer(use_cache=True)
        doc_index = indexer.index(pdf_path)

        # Extract full text for word count
        extractor = TextExtractor(PdfPlumberExtractor())
        full_text = extractor.extract(pdf_path)
        total_words = len(full_text.split()) if full_text else 0

        # Calculate reading time
        reading_minutes = round(total_words / wpm) if wpm > 0 else 0

        # Build section word counts for papers
        section_stats = []
        if doc_index.type == "paper" and doc_index.sections:
            for section in doc_index.sections:
                # Extract text for section's page range (0-indexed pages)
                start_page = section.pages[0] - 1  # Convert to 0-indexed
                end_page = section.pages[1]  # End is exclusive in range
                pages = list(range(start_page, end_page))
                section_text = extractor.extract(pdf_path, pages=pages)
                word_count = len(section_text.split()) if section_text else 0
                section_stats.append({
                    "id": section.id,
                    "title": section.title,
                    "pages": list(section.pages),
                    "word_count": word_count,
                })

        # Build result
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "pages": doc_index.pages,
            "words": total_words,
            "figures": len(doc_index.figures),
            "tables": len(doc_index.tables),
            "references": doc_index.refs_count,
            "reading_time": {
                "minutes": reading_minutes,
                "wpm": wpm,
            },
        }

        # Add metadata if available
        if doc_index.title or doc_index.authors:
            result["metadata"] = {}
            if doc_index.title:
                result["metadata"]["title"] = doc_index.title
            if doc_index.authors:
                result["metadata"]["authors"] = doc_index.authors

        # Add sections (for papers) or chapters (for books)
        if section_stats:
            result["sections"] = section_stats
        elif doc_index.type == "book" and doc_index.chapters:
            result["chapters"] = doc_index.chapters

        formatter.output(result)

    except FileNotFoundError:
        console.print(f"[red]File not found:[/red] {pdf_path}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
