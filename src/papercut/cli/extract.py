"""Extract commands for extracting content from PDFs."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()

app = typer.Typer(
    help="Extract content from PDFs.",
    no_args_is_help=True,
)


def parse_pages(pages_str: Optional[str]) -> Optional[list[int]]:
    """Parse page range string like '1-5,8,10-12' into list of page numbers."""
    if not pages_str:
        return None

    pages = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start) - 1, int(end)))  # Convert to 0-indexed
        else:
            pages.append(int(part) - 1)  # Convert to 0-indexed
    return sorted(set(pages))


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
        help="Split text into chunks of this token size",
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
):
    """Extract clean text from PDF, optionally chunked for LLM processing."""
    from papercut.core.text import TextExtractor
    from papercut.extractors.pdfplumber import PdfPlumberExtractor

    extractor = TextExtractor(PdfPlumberExtractor())
    page_list = parse_pages(pages)

    if chunk_size:
        chunks = extractor.extract_chunked(
            pdf_path,
            chunk_size=chunk_size,
            overlap=overlap,
            pages=page_list,
        )
        result = json.dumps({"chunks": chunks, "count": len(chunks)}, indent=2)
    else:
        result = extractor.extract(pdf_path, pages=page_list)

    if output:
        output.write_text(result)
        console.print(f"[green]Saved to:[/green] {output}")
    else:
        console.print(result)


@app.command()
def tables(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for tables (default: stdout as JSON)",
    ),
    format: str = typer.Option(
        "csv",
        "--format",
        "-f",
        help="Output format: csv or json",
    ),
    pages: Optional[str] = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range to extract (e.g., '1-5,8,10-12')",
    ),
):
    """Extract tables from PDF to CSV or JSON."""
    from papercut.core.tables import TableExtractor
    from papercut.extractors.pdfplumber import PdfPlumberExtractor

    extractor = TableExtractor(PdfPlumberExtractor())
    page_list = parse_pages(pages)

    extracted_tables = extractor.extract(pdf_path, pages=page_list)

    if not extracted_tables:
        console.print("[yellow]No tables found in PDF.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[green]Found {len(extracted_tables)} table(s)[/green]")

    if output:
        output.mkdir(parents=True, exist_ok=True)
        for i, table in enumerate(extracted_tables, 1):
            if format == "csv":
                file_path = output / f"table_{i}.csv"
                file_path.write_text(table.to_csv())
            else:
                file_path = output / f"table_{i}.json"
                file_path.write_text(table.to_json())
            console.print(f"  Saved: {file_path}")
    else:
        # Output to stdout as JSON
        tables_data = [
            {"page": t.page, "rows": len(t.data), "data": t.data} for t in extracted_tables
        ]
        console.print(json.dumps(tables_data, indent=2))


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
        "bibtex",
        "--format",
        "-f",
        help="Output format: bibtex or json",
    ),
):
    """Extract references/bibliography from PDF to BibTeX or JSON."""
    from papercut.core.references import ReferenceExtractor
    from papercut.extractors.pdfplumber import PdfPlumberExtractor

    extractor = ReferenceExtractor(PdfPlumberExtractor())
    refs = extractor.extract(pdf_path)

    if not refs:
        console.print("[yellow]No references found in PDF.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[green]Found {len(refs)} reference(s)[/green]")

    if format == "bibtex":
        result = "\n\n".join(ref.to_bibtex() for ref in refs)
    else:
        result = json.dumps([ref.to_dict() for ref in refs], indent=2)

    if output:
        output.write_text(result)
        console.print(f"[green]Saved to:[/green] {output}")
    else:
        console.print(result)
