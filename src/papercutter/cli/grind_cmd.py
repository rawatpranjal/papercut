"""Grind command for Papercutter Factory.

Extracts evidence from papers based on the configured schema.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from papercutter.grinding import (
    ExtractionProgress,
    ExtractionSchema,
    Extractor,
    Synthesizer,
)
from papercutter.grinding.schema import FieldType, SchemaField
from papercutter.project.manager import ProjectManager

console = Console()


def grind(
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for extraction matrix (CSV or JSON).",
    ),
    synthesize: bool = typer.Option(
        True,
        "--synthesize/--no-synthesize",
        help="Generate one-pagers and appendix rows.",
    ),
    directory: Path = typer.Option(
        Path("."),
        "--dir",
        "-d",
        help="Project directory.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed progress.",
    ),
):
    """Extract evidence from ingested papers.

    This command:
    1. Reads the extraction schema from config
    2. Extracts structured data from each paper using LLM
    3. Generates paper summaries (one-pagers) and contribution statements
    4. Outputs the extraction matrix

    Examples:
        papercutter grind                        # Extract and save to project
        papercutter grind -o matrix.csv          # Export to CSV
        papercutter grind --no-synthesize        # Skip summaries
    """
    directory = Path(directory).resolve()
    manager = ProjectManager(directory)

    # Check if project exists
    if not manager.exists():
        console.print("[red]No project found. Run 'papercutter init' first.[/red]")
        raise typer.Exit(1)

    # Load project
    manager.load()

    # Check for schema
    if not manager.config.grinding.columns:
        console.print("[yellow]No extraction schema configured.[/yellow]")
        console.print("Run 'papercutter configure' first.")
        raise typer.Exit(1)

    # Check for ingested papers
    markdown_dir = manager.project_dir / "markdown"
    md_files = list(markdown_dir.glob("*.md")) if markdown_dir.exists() else []

    if not md_files:
        console.print("[yellow]No ingested papers found.[/yellow]")
        console.print("Run 'papercutter ingest' first.")
        raise typer.Exit(1)

    console.print(f"[bold]Processing {len(md_files)} papers...[/bold]")

    # Build schema from config
    schema = _build_schema(manager)
    console.print(f"  Schema: {len(schema.fields)} fields")

    # Create extractor
    extractor = Extractor(schema)

    # Progress tracking
    def _progress_callback(p: ExtractionProgress) -> None:
        if verbose:
            status = "[green]done[/green]" if p.status == "completed" else f"[yellow]{p.status}[/yellow]"
            console.print(f"  {p.current}/{p.total}: {p.paper_id} - {status}")

    # Run extraction
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting evidence...", total=len(md_files))

        def _update_progress(p: ExtractionProgress) -> None:
            progress.update(task, completed=p.current)
            if verbose:
                _progress_callback(p)

        matrix, result = extractor.extract_from_directory(
            markdown_dir, progress_callback=_update_progress
        )

    console.print(
        f"[green]Extracted from {result.papers_succeeded}/{result.papers_processed} papers[/green]"
    )

    # Generate synthesis
    if synthesize:
        console.print()
        console.print("[bold]Generating summaries...[/bold]")

        synthesizer = Synthesizer()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Synthesizing...", total=len(list(matrix)))

            def _synth_progress(current: int, total: int, paper_id: str) -> None:
                progress.update(task, completed=current)

            synthesis_results = synthesizer.synthesize_matrix(
                matrix,
                markdown_dir,
                progress_callback=_synth_progress,
            )

        succeeded = sum(1 for r in synthesis_results if not r.error)
        console.print(f"[green]Generated {succeeded} summaries[/green]")

    # Save results
    output_path = output
    if output_path:
        output_path = Path(output_path)
        if output_path.suffix == ".csv":
            matrix.to_csv(output_path)
        else:
            matrix.to_json(output_path)
        console.print(f"Matrix saved to: {output_path}")
    else:
        # Save to project
        matrix_path = manager.project_dir / "matrix.json"
        matrix.to_json(matrix_path)
        console.print(f"Matrix saved to: {matrix_path}")

        # Also save CSV
        csv_path = manager.project_dir / "matrix.csv"
        matrix.to_csv(csv_path)
        console.print(f"CSV saved to: {csv_path}")

    # Display summary
    console.print()
    summary = matrix.summary()
    console.print("[bold]Extraction summary:[/bold]")
    console.print(f"  Papers: {summary['paper_count']}")
    console.print(f"  Fields: {summary['field_count']}")

    if verbose:
        console.print("  Field completeness:")
        for field, stats in summary["fields"].items():
            console.print(f"    {field}: {stats['completeness']}")

    if result.errors:
        console.print(f"  [yellow]Errors: {len(result.errors)}[/yellow]")

    console.print()
    console.print("Next: Run [bold]papercutter report[/bold] to generate the review")


def _build_schema(manager: ProjectManager) -> ExtractionSchema:
    """Build ExtractionSchema from project config."""
    schema = ExtractionSchema(
        name=manager.config.name,
        description="Configured extraction schema",
    )

    for col in manager.config.grinding.columns:
        try:
            field_type = FieldType(col.type)
        except ValueError:
            field_type = FieldType.TEXT

        schema.fields.append(
            SchemaField(
                key=col.key,
                description=col.description,
                type=field_type,
                required=col.required,
                options=col.options,
                example=col.example,
            )
        )

    return schema
