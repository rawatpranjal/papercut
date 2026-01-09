"""Configure command for Papercutter Factory.

Auto-generates extraction schema by sampling papers and using LLM.
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from papercutter.grinding import SchemaGenerator, generate_default_schema
from papercutter.project.manager import ProjectManager
from papercutter.project.state import SchemaColumn

console = Console()


def configure(
    auto: bool = typer.Option(
        True,
        "--auto/--manual",
        help="Auto-generate schema using LLM vs manual setup.",
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Use a predefined template (economics, medical).",
    ),
    sample_count: int = typer.Option(
        3,
        "--samples",
        "-s",
        help="Number of papers to sample for auto-generation.",
    ),
    directory: Path = typer.Option(
        Path("."),
        "--dir",
        "-d",
        help="Project directory.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output schema file (defaults to config.yaml in project).",
    ),
):
    """Configure the extraction schema.

    This command sets up what data to extract from each paper:

    1. **Auto mode** (default): Samples papers and uses LLM to suggest columns
    2. **Template mode**: Uses a predefined schema for common domains
    3. **Manual mode**: Creates a minimal schema for you to edit

    After running, edit .papercutter/config.yaml to customize the schema.

    Examples:
        papercutter configure                    # Auto-generate
        papercutter configure --template economics
        papercutter configure --manual           # Start from scratch
    """
    directory = Path(directory).resolve()
    manager = ProjectManager(directory)

    # Check if project exists
    if not manager.exists():
        console.print("[red]No project found. Run 'papercutter init' first.[/red]")
        raise typer.Exit(1)

    # Load project
    manager.load()

    # Check for ingested papers
    markdown_dir = manager.project_dir / "markdown"
    md_files = list(markdown_dir.glob("*.md")) if markdown_dir.exists() else []

    if not md_files and auto and not template:
        console.print("[yellow]No ingested papers found.[/yellow]")
        console.print("Run 'papercutter ingest' first, or use --template")
        raise typer.Exit(1)

    # Generate schema
    if template:
        schema = _get_template_schema(template)
        console.print(f"[bold]Using '{template}' template[/bold]")

    elif auto and md_files:
        console.print(f"[bold]Sampling {min(sample_count, len(md_files))} papers...[/bold]")

        generator = SchemaGenerator(sample_count=sample_count)

        with console.status("Generating schema with LLM..."):
            result = generator.generate(md_files, schema_name=manager.config.name)

        if result.errors:
            console.print(f"[yellow]Warnings: {result.errors}[/yellow]")

        if not result.schema or not result.suggestions:
            console.print("[red]Schema generation failed. Using default schema.[/red]")
            schema = generate_default_schema()
        else:
            schema = result.schema
            console.print(f"[green]Generated {len(result.suggestions)} fields[/green]")

    else:
        # Manual mode - use default schema
        console.print("[bold]Creating default schema...[/bold]")
        schema = generate_default_schema()

    # Convert to project config format
    columns = []
    for field in schema.fields:
        columns.append(
            SchemaColumn(
                key=field.key,
                description=field.description,
                type=field.type.value,
                required=field.required,
                options=field.options,
                example=field.example,
            )
        )

    manager.config.grinding.columns = columns

    # Save
    if output:
        output = Path(output)
        schema.save(output)
        console.print(f"Schema saved to: {output}")
    else:
        manager.save()
        console.print(f"Config saved to: {manager.config_path}")

    # Display schema
    console.print()
    _display_schema(columns)

    console.print()
    console.print(
        f"Edit [bold]{manager.config_path}[/bold] to customize the schema."
    )
    console.print()
    console.print("Next: Run [bold]papercutter grind[/bold] to extract evidence")


def _get_template_schema(template: str):
    """Get a predefined template schema."""
    from papercutter.grinding.schema import (
        create_economics_schema,
        create_medical_schema,
    )

    templates = {
        "economics": create_economics_schema,
        "medical": create_medical_schema,
    }

    if template.lower() not in templates:
        console.print(f"[red]Unknown template: {template}[/red]")
        console.print(f"Available: {', '.join(templates.keys())}")
        raise typer.Exit(1)

    return templates[template.lower()]()


def _display_schema(columns: list[SchemaColumn]) -> None:
    """Display schema in a table."""
    table = Table(title="Extraction Schema")
    table.add_column("Field", style="bold")
    table.add_column("Type")
    table.add_column("Description")
    table.add_column("Required")

    for col in columns:
        table.add_row(
            col.key,
            col.type,
            col.description[:50] + "..." if len(col.description) > 50 else col.description,
            "Yes" if col.required else "No",
        )

    console.print(table)
