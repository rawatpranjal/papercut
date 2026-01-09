"""Read command for extracting text from specific parts of PDFs."""

from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from papercutter.cli.extract import parse_pages
from papercutter.output import get_formatter

console = Console()


def _validate_pdf_path(pdf_path: Path) -> None:
    """Validate that a PDF path exists and is a file."""
    if not pdf_path.exists():
        console.print(f"[red]File not found:[/red] {pdf_path}")
        raise typer.Exit(1)
    if not pdf_path.is_file():
        console.print(f"[red]Not a file:[/red] {pdf_path}")
        raise typer.Exit(1)


def read(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    pages: str | None = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range: '5' or '5-10' or '5,8,10-12'",
    ),
    section: str | None = typer.Option(
        None,
        "--section",
        "-s",
        help="Section ID or title (requires prior indexing)",
    ),
    chapter: int | None = typer.Option(
        None,
        "--chapter",
        "-c",
        help="Chapter ID (for books, requires prior indexing)",
    ),
    all_text: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Extract all text from document",
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
    """Extract text from specific parts of a PDF.

    Returns JSON with text content for LLM processing.
    Uses caching to speed up repeated queries.

    Examples:

        papercutter read paper.pdf --pages 10-14

        papercutter read paper.pdf --section "Methods"

        papercutter read book.pdf --chapter 5

        papercutter read paper.pdf --all
    """
    from papercutter.extractors.pdfplumber import PdfPlumberExtractor
    from papercutter.legacy.cache import get_cache
    from papercutter.legacy.core.text import TextExtractor
    from papercutter.legacy.index import DocumentIndexer

    _validate_pdf_path(pdf_path)

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)
    cache = get_cache()
    extractor = TextExtractor(PdfPlumberExtractor())

    try:
        # Determine what to extract
        query: dict[str, Any]
        if all_text:
            text = extractor.extract(pdf_path)
            query = {"all": True}

        elif pages:
            page_list = parse_pages(pages) or []

            # Check cache
            if len(page_list) > 0:
                start, end = min(page_list), max(page_list)
                cached_text = cache.get_pages(pdf_path, start + 1, end + 1)
                if cached_text:
                    text = cached_text
                    query = {"pages": [start + 1, end + 1], "cached": True}
                else:
                    text = extractor.extract(pdf_path, pages=page_list)
                    cache.set_pages(pdf_path, start + 1, end + 1, text)
                    query = {"pages": [start + 1, end + 1]}
            else:
                text = ""
                query = {"pages": []}

        elif section:
            # Need to get index first
            indexer = DocumentIndexer()
            doc_index = indexer.index(pdf_path)

            # Find section by ID or title
            found_section = None
            for s in doc_index.sections:
                if str(s.id) == section or section.lower() in s.title.lower():
                    found_section = s
                    break

            if not found_section:
                console.print(f"[red]Section not found:[/red] {section}")
                console.print("[dim]Run 'papercutter index' to see available sections[/dim]")
                raise typer.Exit(1)

            # Extract pages for this section
            # pages is (start_1idx, end_1idx) - both 1-indexed, end is inclusive
            start_0idx = found_section.pages[0] - 1  # Convert to 0-indexed
            end_0idx = found_section.pages[1] - 1    # Convert to 0-indexed
            # Ensure valid range (end >= start)
            end_0idx = max(end_0idx, start_0idx)
            page_list = list(range(start_0idx, end_0idx + 1))  # +1 because range is exclusive
            text = extractor.extract(pdf_path, pages=page_list)
            query = {
                "section": found_section.title,
                "section_id": found_section.id,
                "pages": list(found_section.pages),
            }

        elif chapter:
            # Need to get index first
            indexer = DocumentIndexer()
            doc_index = indexer.index(pdf_path, doc_type="book")

            # Find chapter by ID
            found_chapter = None
            for ch in doc_index.chapters:
                if ch["id"] == chapter:
                    found_chapter = ch
                    break

            if not found_chapter:
                console.print(f"[red]Chapter not found:[/red] {chapter}")
                console.print("[dim]Run 'papercutter chapters' to see available chapters[/dim]")
                raise typer.Exit(1)

            # Extract pages for this chapter
            # pages is [start_1idx, end_1idx] - both 1-indexed, end is inclusive
            start_0idx = found_chapter["pages"][0] - 1  # Convert to 0-indexed
            end_0idx = found_chapter["pages"][1] - 1    # Convert to 0-indexed
            # Ensure valid range (end >= start)
            end_0idx = max(end_0idx, start_0idx)
            page_list = list(range(start_0idx, end_0idx + 1))  # +1 because range is exclusive
            text = extractor.extract(pdf_path, pages=page_list)
            query = {
                "chapter": found_chapter["title"],
                "chapter_id": found_chapter["id"],
                "pages": found_chapter["pages"],
            }

        else:
            console.print("[red]Specify --pages, --section, --chapter, or --all[/red]")
            raise typer.Exit(1)

        # Build result
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "query": query,
            "content": {
                "text": text,
                "word_count": len(text.split()) if text else 0,
                "char_count": len(text) if text else 0,
            },
        }

        formatter.output(result)

    except FileNotFoundError:
        console.print(f"[red]File not found:[/red] {pdf_path}")
        raise typer.Exit(1)
    except Exception as e:
        error_result = {
            "success": False,
            "file": str(pdf_path.name),
            "error": str(e),
        }
        formatter.output(error_result)
        raise typer.Exit(1)


