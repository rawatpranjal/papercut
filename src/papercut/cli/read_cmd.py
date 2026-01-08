"""Read command for extracting text from specific parts of PDFs."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from papercut.output import get_formatter

console = Console()


def read(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range: '5' or '5-10' or '5,8,10-12'",
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Section ID or title (requires prior indexing)",
    ),
    chapter: Optional[int] = typer.Option(
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

        papercut read paper.pdf --pages 10-14

        papercut read paper.pdf --section "Methods"

        papercut read book.pdf --chapter 5

        papercut read paper.pdf --all
    """
    from papercut.cache import get_cache
    from papercut.core.text import TextExtractor
    from papercut.extractors.pdfplumber import PdfPlumberExtractor
    from papercut.index import DocumentIndexer

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)
    cache = get_cache()
    extractor = TextExtractor(PdfPlumberExtractor())

    try:
        # Determine what to extract
        if all_text:
            text = extractor.extract(pdf_path)
            query = {"all": True}

        elif pages:
            page_list = _parse_pages(pages)

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
                console.print("[dim]Run 'papercut index' to see available sections[/dim]")
                raise typer.Exit(1)

            # Extract pages for this section
            page_list = list(range(found_section.pages[0] - 1, found_section.pages[1]))
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
                console.print("[dim]Run 'papercut chapters' to see available chapters[/dim]")
                raise typer.Exit(1)

            # Extract pages for this chapter
            page_list = list(range(found_chapter["pages"][0] - 1, found_chapter["pages"][1]))
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


def _parse_pages(pages_str: str) -> list[int]:
    """Parse page range string into list of 0-indexed page numbers.

    Args:
        pages_str: Page specification like '5' or '5-10' or '5,8,10-12'

    Returns:
        List of 0-indexed page numbers.
    """
    pages = []

    for part in pages_str.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            start, end = part.split("-", 1)
            start_int = int(start)
            end_int = int(end)
            pages.extend(range(start_int - 1, end_int))  # Convert to 0-indexed
        else:
            pages.append(int(part) - 1)  # Convert to 0-indexed

    return sorted(set(pages))
