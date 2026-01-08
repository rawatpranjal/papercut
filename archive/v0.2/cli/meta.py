"""Meta-analysis commands for batch extraction from papers."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from papercut.exceptions import PapercutError

console = Console()

app = typer.Typer(
    help="Extract structured data from papers for meta-analysis.",
    no_args_is_help=True,
)


@app.command("extract")
def extract(
    paths: list[Path] = typer.Argument(..., help="PDF files or directory of PDFs"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (.json or .csv)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model to use",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Search directories recursively",
    ),
):
    """Extract structured data from one or more papers.

    Extracts study information, methodology, data sources, and results
    in a structured format suitable for meta-analysis.

    Examples:

        papercut meta extract paper.pdf

        papercut meta extract papers/*.pdf -o results.csv

        papercut meta extract papers/ -r -o results.json
    """
    from papercut.meta.batch import BatchExtractor

    # Collect all PDF paths
    pdf_paths = []
    for path in paths:
        if path.is_dir():
            pattern = "**/*.pdf" if recursive else "*.pdf"
            pdf_paths.extend(path.glob(pattern))
        elif path.suffix.lower() == ".pdf":
            pdf_paths.append(path)
        else:
            console.print(f"[yellow]Skipping non-PDF:[/yellow] {path}")

    if not pdf_paths:
        console.print("[red]No PDF files found[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Found {len(pdf_paths)} PDF(s)[/green]")

    try:
        extractor = BatchExtractor(model=model)

        # Extract with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting...", total=len(pdf_paths))

            def on_progress(i: int, total: int, path: Path):
                progress.update(task, advance=1, description=f"Processing {path.name}")

            batch_result = extractor.extract_batch(pdf_paths, on_progress=on_progress)

        # Report results
        console.print()
        console.print(f"[green]Successful:[/green] {len(batch_result.successful)}")
        if batch_result.failed:
            console.print(f"[red]Failed:[/red] {len(batch_result.failed)}")
            for r in batch_result.failed:
                console.print(f"  - {r.source_path.name}: {r.error}")

        # Output
        if output:
            suffix = output.suffix.lower()
            if suffix == ".csv":
                content = batch_result.to_csv()
            else:
                content = batch_result.to_json()

            output.write_text(content)
            console.print(f"\n[green]Saved:[/green] {output}")

        else:
            # Display summary table
            if batch_result.successful:
                _display_summary(batch_result)

    except PapercutError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        raise typer.Exit(e.exit_code)


def _display_summary(batch_result) -> None:
    """Display a summary table of extraction results."""
    table = Table(title="Extraction Summary")
    table.add_column("Paper", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Year", style="green")
    table.add_column("Method", style="yellow")
    table.add_column("N", style="magenta")

    for result in batch_result.successful:
        title = result.get("study_info", "title", default="—")
        if len(title) > 40:
            title = title[:37] + "..."

        year = result.get("study_info", "year", default="—")
        method = result.get("methodology", "identification_strategy", default="—")
        n = result.get("data", "sample_size", default="—")

        table.add_row(
            result.source_path.name[:30],
            str(title),
            str(year),
            str(method),
            str(n),
        )

    console.print()
    console.print(table)


@app.command("schema")
def schema():
    """Show the extraction schema for meta-analysis.

    Displays the JSON structure that will be extracted from papers.
    """
    schema_text = """
{
  "study_info": {
    "title": "string",
    "authors": ["string"],
    "year": integer,
    "journal": "string or null"
  },
  "methodology": {
    "identification_strategy": "string (RCT, DiD, RDD, IV, OLS, etc.)",
    "estimator": "string or null",
    "controls": ["string"],
    "robustness_checks": ["string"]
  },
  "data": {
    "source": "string",
    "sample_size": integer or null,
    "time_period": "string or null",
    "geographic_scope": "string or null",
    "unit_of_analysis": "string"
  },
  "results": {
    "main_outcome": "string",
    "main_effect": number or null,
    "effect_unit": "string (percentage points, percent, dollars, etc.)",
    "standard_error": number or null,
    "confidence_interval": [number, number] or null,
    "p_value": number or null,
    "statistical_significance": boolean or null
  },
  "heterogeneity": [
    {
      "subgroup": "string",
      "effect": number or null,
      "se": number or null
    }
  ]
}
"""
    console.print(schema_text)
