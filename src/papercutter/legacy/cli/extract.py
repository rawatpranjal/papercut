"""Extract commands for extracting content from PDFs."""

import json
from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console

from papercutter.cli.utils import handle_errors, is_quiet
from papercutter.output import get_formatter

app = typer.Typer(
    help="Extract content from PDFs.",
    no_args_is_help=True,
)


def _get_console() -> Console:
    """Get a console for output messages."""
    return Console()


def _validate_pdf_path(pdf_path: Path) -> None:
    """Validate that a PDF path exists and is a file.

    Args:
        pdf_path: Path to validate.

    Raises:
        typer.BadParameter: If path doesn't exist or isn't a file.
    """
    if not pdf_path.exists():
        raise typer.BadParameter(f"PDF file not found: {pdf_path}")
    if not pdf_path.is_file():
        raise typer.BadParameter(f"Not a file: {pdf_path}")


def parse_pages(pages_str: str | None) -> list[int] | None:
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

    pages: list[int] = []
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


def _read_pdf_batch_file(batch_file: Path) -> list[tuple[int, Path]]:
    """Read PDF paths from a batch file."""
    console = _get_console()
    if not batch_file.exists():
        console.print(f"[red]Error:[/red] Batch file not found: {batch_file}")
        raise typer.Exit(1)

    entries: list[tuple[int, Path]] = []
    with open(batch_file, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            entries.append((line_no, Path(value).expanduser()))
    return entries


def _run_text_batch(
    batch_file: Path,
    output_dir: Path,
    build_result: Callable[[Path], dict],
) -> None:
    """Run text extraction for multiple PDFs."""
    entries = _read_pdf_batch_file(batch_file)
    console = _get_console()
    quiet_mode = is_quiet()

    if not entries:
        if not quiet_mode:
            console.print(f"[yellow]No PDF paths found in {batch_file}[/yellow]")
        raise typer.Exit(0)

    output_dir.mkdir(parents=True, exist_ok=True)

    successes = 0
    failures: list[tuple[int, str, str]] = []

    for line_no, pdf_path in entries:
        try:
            _validate_pdf_path(pdf_path)
            result = build_result(pdf_path)
            output_file = output_dir / f"{pdf_path.stem}.json"
            output_file.write_text(json.dumps(result, indent=2))
            successes += 1
            if not quiet_mode:
                console.print(f"  [green]Saved:[/green] {output_file}")
        except Exception as exc:
            failures.append((line_no, str(pdf_path), str(exc)))
            if not quiet_mode:
                console.print(f"  [red]Failed line {line_no}:[/red] {exc}")

    if not quiet_mode:
        console.print(
            f"[bold]Batch complete:[/bold] [green]{successes} success[/green], "
            f"[red]{len(failures)} failed[/red]"
        )

    if failures:
        raise typer.Exit(1)


@app.command()
@handle_errors
def text(
    pdf_path: Path | None = typer.Argument(None, help="Path to PDF file"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout)",
    ),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        help="File with PDF paths (one per line) for batch extraction.",
    ),
    chunk_size: int | None = typer.Option(
        None,
        "--chunk-size",
        help="Split text into chunks of this character size",
    ),
    overlap: int = typer.Option(
        200,
        "--overlap",
        help="Overlap between chunks (in characters)",
    ),
    pages: str | None = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range to extract (e.g., '1-5,8,10-12')",
    ),
    include_metadata: bool = typer.Option(
        False,
        "--include-metadata",
        "-m",
        help="Include chunk metadata (page, section, figure/table refs)",
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
    Use --include-metadata with --chunk-size for LLM-ready chunks with
    page numbers, section info, and figure/table references.
    """
    from papercutter.extractors.pdfplumber import PdfPlumberExtractor
    from papercutter.legacy.core.text import TextExtractor

    console = _get_console()
    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())
    backend = PdfPlumberExtractor()
    extractor = TextExtractor(backend)
    page_list = parse_pages(pages)
    metadata_warning_shown = False

    def validate_pages(target_pdf: Path, page_indices: list[int] | None) -> None:
        """Validate that requested pages exist in the document."""
        if page_indices is None:
            return
        page_count = backend.get_page_count(target_pdf)
        invalid = [p + 1 for p in page_indices if p >= page_count]  # Convert to 1-indexed
        if invalid:
            raise typer.BadParameter(
                f"Pages {invalid} out of range (document has {page_count} pages)"
            )

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

    def build_result(target_pdf: Path) -> dict:
        nonlocal metadata_warning_shown

        # Validate page range before extraction
        validate_pages(target_pdf, page_list)

        if chunk_size:
            if include_metadata:
                from papercutter.legacy.index import DocumentIndexer

                indexer = DocumentIndexer(use_cache=True)
                doc_index = indexer.index(target_pdf)
                sections = doc_index.sections if doc_index.type == "paper" else []

                chunks = extractor.extract_chunked_with_metadata(
                    target_pdf,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    pages=page_list,
                    sections=sections,
                )
                return {
                    "success": True,
                    "file": str(target_pdf.name),
                    "chunked": True,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "count": len(chunks),
                    "chunks": [c.to_dict() for c in chunks],
                }

            text_chunks = extractor.extract_chunked(
                target_pdf,
                chunk_size=chunk_size,
                overlap=overlap,
                pages=page_list,
            )
            return {
                "success": True,
                "file": str(target_pdf.name),
                "chunked": True,
                "chunk_size": chunk_size,
                "overlap": overlap,
                "count": len(text_chunks),
                "chunks": text_chunks,
            }

        if include_metadata:
            if not metadata_warning_shown:
                console.print("[yellow]Warning:[/yellow] --include-metadata requires --chunk-size")
                metadata_warning_shown = True
            text_content = extractor.extract(target_pdf, pages=page_list)
            return {
                "success": True,
                "file": str(target_pdf.name),
                "pages": list(page_list) if page_list else "all",
                "content": {
                    "text": text_content,
                    "word_count": len(text_content.split()),
                    "char_count": len(text_content),
                },
            }

        text_content = extractor.extract(target_pdf, pages=page_list)
        return {
            "success": True,
            "file": str(target_pdf.name),
            "pages": list(page_list) if page_list else "all",
            "content": {
                "text": text_content,
                "word_count": len(text_content.split()),
                "char_count": len(text_content),
            },
        }

    if batch:
        if output is None:
            raise typer.BadParameter("--output directory is required when using --batch")
        if output.exists() and not output.is_dir():
            raise typer.BadParameter("--output must be a directory when using --batch")
        _run_text_batch(batch, output, build_result)
        return

    if pdf_path is None:
        raise typer.BadParameter("pdf_path is required unless --batch is provided")

    _validate_pdf_path(pdf_path)
    result = build_result(pdf_path)

    if output:
        json_output = json.dumps(result, indent=2)
        output.write_text(json_output)
        if not is_quiet():
            console.print(f"[green]Saved:[/green] {output}")
    else:
        formatter.output(result)


@app.command()
@handle_errors
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
    from papercutter.extractors.pdfplumber import PdfPlumberExtractor
    from papercutter.legacy.cache import get_cache
    from papercutter.legacy.core.tables import TableExtractor

    _validate_pdf_path(pdf_path)

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())
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
@handle_errors
def tables(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for tables",
    ),
    pages: str | None = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range to extract (e.g., '1-5,8,10-12')",
    ),
    strictness: str = typer.Option(
        "standard",
        "--strictness",
        "-s",
        help="Validation strictness: permissive, standard, or strict",
    ),
    table_strategy: str | None = typer.Option(
        None,
        "--table-strategy",
        help="Table detection strategy: 'lines' (default) or 'text'",
    ),
    snap_tolerance: int | None = typer.Option(
        None,
        "--snap-tolerance",
        help="Tolerance for snapping edges together (default: 3)",
    ),
    join_tolerance: int | None = typer.Option(
        None,
        "--join-tolerance",
        help="Tolerance for joining table elements (default: 3)",
    ),
    edge_min_length: int | None = typer.Option(
        None,
        "--edge-min-length",
        help="Minimum edge length to consider (default: 3)",
    ),
    min_words_vertical: int | None = typer.Option(
        None,
        "--min-words-vertical",
        help="Min words for vertical boundary detection (default: 3)",
    ),
    min_words_horizontal: int | None = typer.Option(
        None,
        "--min-words-horizontal",
        help="Min words for horizontal boundary detection (default: 1)",
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
    llm: bool = typer.Option(
        False,
        "--llm",
        help="Force LLM vision extraction for all pages (requires API key)",
    ),
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Never use LLM, even for low-confidence tables",
    ),
    confidence: float = typer.Option(
        0.5,
        "--confidence",
        "-c",
        help="Confidence threshold for LLM fallback (0.0-1.0)",
    ),
    estimate: bool = typer.Option(
        False,
        "--estimate",
        help="Show cost estimate without running LLM extraction",
    ),
    vision_model: str = typer.Option(
        "gpt-4o-mini",
        "--vision-model",
        help="Model to use for vision extraction",
    ),
):
    """Extract all tables from PDF.

    Returns JSON with all tables. Supports optional LLM vision fallback
    for low-confidence extractions.

    Strictness levels:
    - permissive: Minimal filtering, may include false positives
    - standard: Balanced filtering (default)
    - strict: Aggressive filtering, may miss some valid tables

    Table detection strategies:
    - lines: Detect tables using visible lines/borders (default, best for formal tables)
    - text: Detect tables using text alignment (better for borderless tables)

    LLM fallback modes:
    - Default: Try traditional first, LLM fallback for confidence < threshold
    - --llm: Force LLM vision extraction for all pages
    - --offline: Never use LLM (traditional extraction only)
    - --estimate: Show cost estimate without running LLM

    Examples:
        papercutter extract tables paper.pdf --table-strategy text
        papercutter extract tables paper.pdf --snap-tolerance 5 --strictness permissive
        papercutter extract tables paper.pdf --confidence 0.7 --json
        papercutter extract tables paper.pdf --llm --json
        papercutter extract tables paper.pdf --estimate
    """
    from papercutter.extractors.pdfplumber import PdfPlumberExtractor
    from papercutter.legacy.core.tables import TableExtractor

    _validate_pdf_path(pdf_path)

    # Validate strictness
    valid_levels = ("permissive", "standard", "strict")
    if strictness not in valid_levels:
        raise typer.BadParameter(
            f"Invalid strictness: {strictness}. Must be one of: {', '.join(valid_levels)}"
        )

    # Validate table_strategy
    if table_strategy and table_strategy not in ("lines", "text"):
        raise typer.BadParameter(
            f"Invalid table-strategy: {table_strategy}. Must be 'lines' or 'text'"
        )

    # Build table_settings dict from CLI options
    table_settings: dict[str, str | int] | None = None
    if any([table_strategy, snap_tolerance, join_tolerance,
            edge_min_length, min_words_vertical, min_words_horizontal]):
        table_settings = {}
        if table_strategy:
            table_settings["vertical_strategy"] = table_strategy
            table_settings["horizontal_strategy"] = table_strategy
        if snap_tolerance is not None:
            table_settings["snap_tolerance"] = snap_tolerance
        if join_tolerance is not None:
            table_settings["join_tolerance"] = join_tolerance
        if edge_min_length is not None:
            table_settings["edge_min_length"] = edge_min_length
        if min_words_vertical is not None:
            table_settings["min_words_vertical"] = min_words_vertical
        if min_words_horizontal is not None:
            table_settings["min_words_horizontal"] = min_words_horizontal

    console = _get_console()
    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())
    backend = PdfPlumberExtractor()
    extractor = TableExtractor(backend, strictness=strictness)
    page_list = parse_pages(pages)

    # Validate page range before extraction
    if page_list is not None:
        page_count = backend.get_page_count(pdf_path)
        invalid = [p + 1 for p in page_list if p >= page_count]  # Convert to 1-indexed
        if invalid:
            raise typer.BadParameter(
                f"Pages {invalid} out of range (document has {page_count} pages)"
            )

    # Handle --estimate flag first
    if estimate:
        cost_info = extractor.estimate_fallback_cost(
            pdf_path,
            pages=page_list,
            confidence_threshold=confidence,
        )
        formatter.output(cost_info)
        return

    # Extract tables with appropriate method
    used_hybrid = False
    used_llm = False

    if llm or (not offline and confidence < 1.0):
        # Use fallback extraction (may use LLM)
        extracted_tables = extractor.extract_with_fallback(
            pdf_path,
            pages=page_list,
            confidence_threshold=confidence,
            force_llm=llm,
            offline=offline,
            vision_model=vision_model,
        )
        used_llm = any(t.extraction_method == "vision-llm" for t in extracted_tables)
    elif table_settings is None:
        # First try default extraction
        extracted_tables = extractor.extract(pdf_path, pages=page_list)

        # If no tables found, try hybrid extraction (both lines and text strategies)
        if len(extracted_tables) == 0:
            extracted_tables = extractor.extract_hybrid(pdf_path, pages=page_list)
            if len(extracted_tables) > 0:
                used_hybrid = True
    else:
        # User specified explicit settings, use those
        extracted_tables = extractor.extract(pdf_path, pages=page_list, table_settings=table_settings)

    tables_data = [
        {
            "id": i + 1,
            "page": t.page,
            "headers": t.headers,
            "rows": t.data,
            "row_count": len(t.data),
            "col_count": t.cols,
            "confidence": round(t.confidence, 2),
            "extraction_method": t.extraction_method,
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
        if not is_quiet():
            console.print(f"[green]Saved {len(extracted_tables)} table(s) to:[/green] {output}")
            if used_hybrid:
                console.print("[dim]Used hybrid extraction (lines + text strategies)[/dim]")
            if used_llm:
                llm_count = sum(1 for t in extracted_tables if t.extraction_method == "vision-llm")
                console.print(f"[dim]Used LLM vision extraction for {llm_count} table(s)[/dim]")
    else:
        if used_hybrid:
            result["hybrid_extraction"] = True
        if used_llm:
            result["llm_extraction"] = True
            result["llm_tables"] = sum(1 for t in extracted_tables if t.extraction_method == "vision-llm")
        formatter.output(result)


@app.command()
@handle_errors
def figure(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    figure_id: int = typer.Option(
        ...,
        "--id",
        "-i",
        help="Figure ID to extract",
    ),
    output: Path | None = typer.Option(
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
    from papercutter.legacy.cache import get_cache
    from papercutter.legacy.core.figures import FigureExtractor

    _validate_pdf_path(pdf_path)

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())
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
@handle_errors
def figures(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for figures",
    ),
    pages: str | None = typer.Option(
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
    from papercutter.legacy.core.figures import FigureExtractor

    _validate_pdf_path(pdf_path)

    console = _get_console()
    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())

    try:
        extractor = FigureExtractor()
        page_list = parse_pages(pages)

        # Validate page range before extraction
        if page_list is not None:
            from papercutter.extractors.pdfplumber import PdfPlumberExtractor
            backend = PdfPlumberExtractor()
            page_count = backend.get_page_count(pdf_path)
            invalid = [p + 1 for p in page_list if p >= page_count]  # Convert to 1-indexed
            if invalid:
                raise typer.BadParameter(
                    f"Pages {invalid} out of range (document has {page_count} pages)"
                )

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
            if not is_quiet():
                console.print(f"[green]Saved {len(extracted_figures)} figure(s) to:[/green] {output}")

        formatter.output(result)

    except ImportError as e:
        result = {"success": False, "error": str(e)}
        formatter.output(result)
        raise typer.Exit(1)


def _infer_refs_format(output_path: Path | None, explicit_format: str) -> str:
    """Infer output format from file extension or explicit flag.

    Args:
        output_path: Output file path (may be None for stdout).
        explicit_format: Explicitly specified format from --format flag.

    Returns:
        Format string: "bibtex" or "json".
    """
    # Explicit non-default format takes precedence
    if explicit_format and explicit_format != "json":
        return explicit_format

    # Infer from file extension
    if output_path:
        ext = output_path.suffix.lower()
        if ext == ".bib":
            return "bibtex"
        elif ext == ".json":
            return "json"

    return explicit_format or "json"


@app.command()
@handle_errors
def refs(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: stdout). Format auto-detected from extension (.bib, .json).",
    ),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: bibtex or json. Overrides extension auto-detection.",
    ),
    search: str | None = typer.Option(
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

    Returns JSON with references data. Output format is auto-detected from
    file extension (.bib for BibTeX, .json for JSON) or can be explicitly
    set with --format.
    """
    from papercutter.extractors.pdfplumber import PdfPlumberExtractor
    from papercutter.legacy.core.references import ReferenceExtractor

    _validate_pdf_path(pdf_path)

    console = _get_console()
    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())
    extractor = ReferenceExtractor(PdfPlumberExtractor())
    all_refs = extractor.extract(pdf_path)

    # Infer format from extension if not explicitly specified
    effective_format = _infer_refs_format(output, format)

    # Filter by search if specified
    if search:
        search_lower = search.lower()
        all_refs = [
            r for r in all_refs
            if search_lower in r.raw_text.lower()
            or (r.title and search_lower in r.title.lower())
            or any(search_lower in a.lower() for a in r.authors)
        ]

    if effective_format == "bibtex":
        # Use a set to track used keys and ensure uniqueness
        used_keys: set[str] = set()
        bibtex_entries = [ref.to_bibtex(used_keys) for ref in all_refs]
        bibtex_output = "\n\n".join(bibtex_entries)
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
        if effective_format == "bibtex":
            output.write_text(bibtex_output)
        else:
            json_output = json.dumps(result, indent=2)
            output.write_text(json_output)
        if not is_quiet():
            console.print(f"[green]Saved:[/green] {output}")
    else:
        formatter.output(result)


def _find_section(sections: list, query: str):
    """Find section by ID or partial title match.

    Args:
        sections: List of Section objects with id, title attributes.
        query: Section ID (as string) or partial title.

    Returns:
        Matched section or None.
    """
    query_lower = query.lower().strip()

    # Try exact ID match first
    for s in sections:
        if str(s.id) == query:
            return s

    # Try exact title match (case-insensitive)
    for s in sections:
        if s.title.lower() == query_lower:
            return s

    # Try partial title match
    for s in sections:
        if query_lower in s.title.lower():
            return s

    return None


@app.command()
@handle_errors
def section(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    section_name: str | None = typer.Option(
        None,
        "--section",
        "-s",
        help="Section name or ID to extract (partial match supported)",
    ),
    list_sections: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all detected sections",
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
    """Extract text from a specific section or list sections.

    Use --list to see all detected sections.
    Use --section to extract a specific section's text.

    Examples:

        papercutter extract section paper.pdf --list

        papercutter extract section paper.pdf --section "Methods"

        papercutter extract section paper.pdf -s 3

        papercutter extract section paper.pdf -s Introduction -o intro.txt
    """
    from papercutter.extractors.pdfplumber import PdfPlumberExtractor
    from papercutter.legacy.core.text import TextExtractor
    from papercutter.legacy.index import DocumentIndexer

    _validate_pdf_path(pdf_path)

    console = _get_console()
    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())

    # Get document index for section detection
    indexer = DocumentIndexer(use_cache=True)
    doc_index = indexer.index(pdf_path)

    if doc_index.type == "book":
        result = {
            "success": False,
            "error": "This document is detected as a book. Use 'papercutter chapters' instead.",
        }
        formatter.output(result)
        raise typer.Exit(1)

    sections = doc_index.sections

    if not sections:
        result = {
            "success": False,
            "error": "No sections detected in this document.",
            "hint": "Try 'papercutter index' to see the full document structure.",
        }
        formatter.output(result)
        raise typer.Exit(1)

    # List mode: show all sections
    if list_sections:
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "count": len(sections),
            "sections": [
                {"id": s.id, "title": s.title, "pages": list(s.pages)}
                for s in sections
            ],
        }
        if output:
            json_output = json.dumps(result, indent=2)
            output.write_text(json_output)
            if not is_quiet():
                console.print(f"[green]Saved:[/green] {output}")
        else:
            formatter.output(result)
        return

    # Extract mode: need a section name
    if not section_name:
        result = {
            "success": False,
            "error": "Please specify --section/-s or --list/-l",
            "hint": "Use --list to see available sections",
        }
        formatter.output(result)
        raise typer.Exit(1)

    # Find matching section
    matched = _find_section(sections, section_name)

    if not matched:
        available = ", ".join(f'"{s.title}"' for s in sections[:5])
        if len(sections) > 5:
            available += f" ... and {len(sections) - 5} more"
        result = {
            "success": False,
            "error": f"Section not found: '{section_name}'",
            "hint": f"Available sections: {available}",
        }
        formatter.output(result)
        raise typer.Exit(1)

    # Extract text for the section
    # pages is (start_1idx, end_1idx) - both 1-indexed, end is inclusive
    extractor = TextExtractor(PdfPlumberExtractor())
    start_0idx = matched.pages[0] - 1  # Convert to 0-indexed
    end_0idx = matched.pages[1] - 1    # Convert to 0-indexed
    # Ensure valid range (end >= start)
    end_0idx = max(end_0idx, start_0idx)
    pages = list(range(start_0idx, end_0idx + 1))  # +1 because range is exclusive
    section_text = extractor.extract(pdf_path, pages=pages)

    result = {
        "success": True,
        "file": str(pdf_path.name),
        "section": {
            "id": matched.id,
            "title": matched.title,
            "pages": list(matched.pages),
        },
        "content": {
            "text": section_text,
            "word_count": len(section_text.split()) if section_text else 0,
            "char_count": len(section_text) if section_text else 0,
        },
    }

    if output:
        # For file output, just save the text content
        output.write_text(section_text)
        if not is_quiet():
            console.print(f"[green]Saved:[/green] {output}")
    else:
        formatter.output(result)
