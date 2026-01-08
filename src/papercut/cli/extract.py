"""Extract commands for extracting content from PDFs."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from papercut.output import get_formatter

console = Console()

app = typer.Typer(
    help="Extract content from PDFs.",
    no_args_is_help=True,
)


def parse_pages(pages_str: Optional[str]) -> Optional[list[int]]:
    """Parse page range string like '1-5,8,10-12' into list of page numbers.

    Args:
        pages_str: Page specification string (e.g., '1-5,8,10-12').

    Returns:
        List of 0-indexed page numbers, or None if no pages specified.

    Raises:
        typer.BadParameter: If the pages string is invalid.
    """
    if not pages_str or not pages_str.strip():
        return None

    pages = []
    try:
        for part in pages_str.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start, end = part.split("-", 1)
                if not start or not end:
                    raise ValueError(f"Invalid range: '{part}' (use format like '1-5')")
                start_int = int(start)
                end_int = int(end)
                if start_int < 1 or end_int < 1:
                    raise ValueError("Page numbers must be positive (1 or greater)")
                if start_int > end_int:
                    raise ValueError(f"Invalid range: {start} > {end}")
                pages.extend(range(start_int - 1, end_int))  # Convert to 0-indexed
            else:
                page_int = int(part)
                if page_int < 1:
                    raise ValueError("Page numbers must be positive (1 or greater)")
                pages.append(page_int - 1)  # Convert to 0-indexed
    except ValueError as e:
        raise typer.BadParameter(f"Invalid pages format: {e}")

    return sorted(set(pages)) if pages else None


@app.command()
def text(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout)",
    ),
    chunk_size: Optional[int] = typer.Option(
        None,
        "--chunk-size",
        help="Split text into chunks of this character size",
    ),
    overlap: int = typer.Option(
        200,
        "--overlap",
        help="Overlap between chunks (in characters)",
    ),
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range to extract (e.g., '1-5,8,10-12')",
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
    """Extract clean text from PDF.

    Returns JSON with text content for LLM processing.
    """
    from papercut.core.text import TextExtractor
    from papercut.extractors.pdfplumber import PdfPlumberExtractor

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)
    extractor = TextExtractor(PdfPlumberExtractor())
    page_list = parse_pages(pages)

    # Validate chunk parameters
    if chunk_size is not None:
        if chunk_size <= 0:
            raise typer.BadParameter("chunk-size must be a positive integer")
        if overlap < 0:
            raise typer.BadParameter("overlap must be non-negative")
        if overlap >= chunk_size:
            raise typer.BadParameter(
                f"overlap ({overlap}) must be less than chunk-size ({chunk_size})"
            )

    if chunk_size:
        chunks = extractor.extract_chunked(
            pdf_path,
            chunk_size=chunk_size,
            overlap=overlap,
            pages=page_list,
        )
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "chunked": True,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "count": len(chunks),
            "chunks": chunks,
        }
    else:
        text_content = extractor.extract(pdf_path, pages=page_list)
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "pages": list(page_list) if page_list else "all",
            "content": {
                "text": text_content,
                "word_count": len(text_content.split()),
                "char_count": len(text_content),
            },
        }

    if output:
        json_output = json.dumps(result, indent=2)
        output.write_text(json_output)
        console.print(f"[green]Saved:[/green] {output}")
    else:
        formatter.output(result)


@app.command()
def table(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    table_id: int = typer.Option(
        ...,
        "--id",
        "-i",
        help="Table ID to extract",
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
    """Extract a single table by ID.

    Returns JSON with table data.
    """
    from papercut.cache import get_cache
    from papercut.core.tables import TableExtractor
    from papercut.extractors.pdfplumber import PdfPlumberExtractor

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)
    cache = get_cache()

    # Check cache first
    cached = cache.get_table(pdf_path, table_id)
    if cached:
        result = {"success": True, "cached": True, "file": str(pdf_path.name), "table": cached}
        formatter.output(result)
        return

    # Extract all tables to find the one we want
    extractor = TableExtractor(PdfPlumberExtractor())
    all_tables = extractor.extract(pdf_path)

    if table_id < 1 or table_id > len(all_tables):
        result = {
            "success": False,
            "error": f"Table {table_id} not found. Document has {len(all_tables)} table(s).",
        }
        formatter.output(result)
        raise typer.Exit(1)

    table_obj = all_tables[table_id - 1]
    table_data = {
        "id": table_id,
        "page": table_obj.page,
        "headers": table_obj.headers,
        "rows": table_obj.data,
        "row_count": len(table_obj.data),
        "col_count": table_obj.cols,
        "csv": table_obj.to_csv(),
    }

    # Cache it
    cache.set_table(pdf_path, table_id, table_data)

    result = {"success": True, "file": str(pdf_path.name), "table": table_data}
    formatter.output(result)


@app.command()
def tables(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for tables",
    ),
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range to extract (e.g., '1-5,8,10-12')",
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
    """Extract all tables from PDF.

    Returns JSON with all tables.
    """
    from papercut.core.tables import TableExtractor
    from papercut.extractors.pdfplumber import PdfPlumberExtractor

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)
    extractor = TableExtractor(PdfPlumberExtractor())
    page_list = parse_pages(pages)

    extracted_tables = extractor.extract(pdf_path, pages=page_list)

    tables_data = [
        {
            "id": i + 1,
            "page": t.page,
            "headers": t.headers,
            "rows": t.data,
            "row_count": len(t.data),
            "col_count": t.cols,
        }
        for i, t in enumerate(extracted_tables)
    ]

    result = {
        "success": True,
        "file": str(pdf_path.name),
        "count": len(tables_data),
        "tables": tables_data,
    }

    if output:
        output.mkdir(parents=True, exist_ok=True)
        for i, t in enumerate(extracted_tables, 1):
            csv_path = output / f"table_{i}.csv"
            csv_path.write_text(t.to_csv())
        console.print(f"[green]Saved {len(extracted_tables)} table(s) to:[/green] {output}")
    else:
        formatter.output(result)


@app.command()
def figure(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    figure_id: int = typer.Option(
        ...,
        "--id",
        "-i",
        help="Figure ID to extract",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path for figure",
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
    """Extract a single figure by ID.

    Returns path to cached figure or saves to specified output.
    """
    from papercut.cache import get_cache
    from papercut.core.figures import FigureExtractor

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)
    cache = get_cache()

    # Check cache first
    cached_path = cache.get_figure_path(pdf_path, figure_id)
    if cached_path:
        if output:
            import shutil
            shutil.copy(cached_path, output)
            result = {"success": True, "file": str(pdf_path.name), "figure_path": str(output)}
        else:
            result = {
                "success": True,
                "cached": True,
                "file": str(pdf_path.name),
                "figure_path": str(cached_path),
            }
        formatter.output(result)
        return

    # Extract figure
    try:
        extractor = FigureExtractor()
        fig = extractor.extract_one(pdf_path, figure_id)

        if not fig:
            result = {"success": False, "error": f"Figure {figure_id} not found"}
            formatter.output(result)
            raise typer.Exit(1)

        # Save to cache or output
        if output:
            fig.save(output)
            fig_path = str(output)
        else:
            fig_path = str(cache.set_figure(pdf_path, figure_id, fig.image_data))

        result = {
            "success": True,
            "file": str(pdf_path.name),
            "figure": fig.to_dict(),
            "figure_path": fig_path,
        }
        formatter.output(result)

    except ImportError as e:
        result = {"success": False, "error": str(e)}
        formatter.output(result)
        raise typer.Exit(1)


@app.command()
def figures(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for figures",
    ),
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range to extract (e.g., '1-5,8,10-12')",
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
    """Extract all figures from PDF.

    Requires PyMuPDF: pip install pymupdf
    """
    from papercut.core.figures import FigureExtractor

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)

    try:
        extractor = FigureExtractor()
        page_list = parse_pages(pages)

        extracted_figures = extractor.extract(pdf_path, pages=page_list)

        figures_data = [fig.to_dict() for fig in extracted_figures]

        result = {
            "success": True,
            "file": str(pdf_path.name),
            "count": len(figures_data),
            "figures": figures_data,
        }

        if output:
            output.mkdir(parents=True, exist_ok=True)
            for fig in extracted_figures:
                fig_path = output / f"fig_{fig.id}.png"
                fig.save(fig_path)
            result["output_dir"] = str(output)
            console.print(f"[green]Saved {len(extracted_figures)} figure(s) to:[/green] {output}")

        formatter.output(result)

    except ImportError as e:
        result = {"success": False, "error": str(e)}
        formatter.output(result)
        raise typer.Exit(1)


@app.command()
def refs(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout)",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: bibtex or json",
    ),
    search: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help="Filter references by search term",
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
    """Extract references/bibliography from PDF.

    Returns JSON with references data.
    """
    from papercut.core.references import ReferenceExtractor
    from papercut.extractors.pdfplumber import PdfPlumberExtractor

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)
    extractor = ReferenceExtractor(PdfPlumberExtractor())
    all_refs = extractor.extract(pdf_path)

    # Filter by search if specified
    if search:
        search_lower = search.lower()
        all_refs = [
            r for r in all_refs
            if search_lower in r.raw.lower()
            or (r.title and search_lower in r.title.lower())
            or any(search_lower in a.lower() for a in r.authors)
        ]

    if format == "bibtex":
        bibtex_output = "\n\n".join(ref.to_bibtex() for ref in all_refs)
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "count": len(all_refs),
            "format": "bibtex",
            "bibtex": bibtex_output,
        }
    else:
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "count": len(all_refs),
            "references": [ref.to_dict() for ref in all_refs],
        }

    if output:
        if format == "bibtex":
            output.write_text(bibtex_output)
        else:
            json_output = json.dumps(result, indent=2)
            output.write_text(json_output)
        console.print(f"[green]Saved:[/green] {output}")
    else:
        formatter.output(result)
