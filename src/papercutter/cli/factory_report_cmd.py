"""Report command for Papercutter Factory.

Generates LaTeX or Markdown reports from extraction results.
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from papercutter.grinding import ExtractionMatrix
from papercutter.project.manager import ProjectManager
from papercutter.reporting import ReportBuilder, ReportContext, ReportFormat
from papercutter.utils.bibtex import BibTeXEntry

console = Console()


def report(
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path.",
    ),
    format: str = typer.Option(
        "latex",
        "--format",
        "-f",
        help="Output format (latex or markdown).",
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Custom template file.",
    ),
    title: str | None = typer.Option(
        None,
        "--title",
        help="Report title (defaults to project name).",
    ),
    author: str | None = typer.Option(
        None,
        "--author",
        "-a",
        help="Author name.",
    ),
    no_summaries: bool = typer.Option(
        False,
        "--no-summaries",
        help="Exclude paper summaries.",
    ),
    no_matrix: bool = typer.Option(
        False,
        "--no-matrix",
        help="Exclude evidence matrix table.",
    ),
    no_appendix: bool = typer.Option(
        False,
        "--no-appendix",
        help="Exclude appendix with contribution statements.",
    ),
    directory: Path = typer.Option(
        Path("."),
        "--dir",
        "-d",
        help="Project directory.",
    ),
):
    """Generate a systematic review report.

    Creates a LaTeX or Markdown document from extraction results including:
    - Evidence matrix table
    - Paper summaries (one-pagers)
    - Appendix with contribution statements

    Examples:
        papercutter report                       # Generate LaTeX
        papercutter report -o review.md -f markdown
        papercutter report --no-summaries        # Matrix only
    """
    directory = Path(directory).resolve()
    manager = ProjectManager(directory)

    # Check if project exists
    if not manager.exists():
        console.print("[red]No project found. Run 'papercutter init' first.[/red]")
        raise typer.Exit(1)

    # Load project
    manager.load()

    # Load extraction matrix
    matrix_path = manager.project_dir / "matrix.json"
    if not matrix_path.exists():
        console.print("[yellow]No extraction matrix found.[/yellow]")
        console.print("Run 'papercutter grind' first.")
        raise typer.Exit(1)

    matrix = ExtractionMatrix.from_json(matrix_path)

    if not matrix.paper_count:
        console.print("[yellow]Extraction matrix is empty.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold]Generating report for {matrix.paper_count} papers...[/bold]")

    # Determine output format
    try:
        output_format = ReportFormat(format.lower())
    except ValueError:
        console.print(f"[red]Invalid format: {format}. Use 'latex' or 'markdown'.[/red]")
        raise typer.Exit(1)

    # Determine output path
    if output is None:
        extension = ".tex" if output_format == ReportFormat.LATEX else ".md"
        output = directory / f"report{extension}"

    output = Path(output)

    # Load bibliography if available
    bibliography = []
    if manager.config.bibtex_path:
        bib_path = directory / manager.config.bibtex_path
        if bib_path.exists():
            bibliography = _load_bibliography(bib_path)
            console.print(f"  Loaded {len(bibliography)} BibTeX entries")

    # Build context
    context = ReportContext(
        title=title or manager.config.name,
        author=author or "",
        matrix=matrix,
        schema=matrix.schema,
        bibliography=bibliography,
        include_summaries=not no_summaries,
        include_matrix=not no_matrix,
        include_appendix=not no_appendix,
        bibliography_style=manager.config.reporting.bibliography_style,
    )

    # Build report
    builder = ReportBuilder(output_format=output_format)

    with console.status("Building report..."):
        content = builder.build(context, template_name=template, output_path=output)

    console.print(f"[green]Report saved to: {output}[/green]")

    # Show stats
    console.print()
    console.print(f"Report includes:")
    console.print(f"  Papers: {matrix.paper_count}")
    if not no_matrix:
        console.print(f"  Matrix fields: {len(matrix.field_keys)}")
    if not no_summaries:
        with_summaries = sum(1 for p in matrix if p.one_pager)
        console.print(f"  Summaries: {with_summaries}")
    if not no_appendix:
        with_appendix = sum(1 for p in matrix if p.appendix_row)
        console.print(f"  Contribution statements: {with_appendix}")

    if output_format == ReportFormat.LATEX:
        console.print()
        console.print(f"Compile with: pdflatex {output}")


def _load_bibliography(bib_path: Path) -> list[BibTeXEntry]:
    """Load BibTeX entries from file."""
    try:
        from papercutter.ingest.matcher import parse_bibtex_file

        return parse_bibtex_file(bib_path)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load BibTeX: {e}[/yellow]")
        return []
