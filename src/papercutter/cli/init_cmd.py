"""Init command for Papercutter Factory.

Creates a new project folder with the required structure.
"""

from pathlib import Path

import typer
from rich.console import Console

from papercutter.project.manager import ProjectManager

console = Console()


def init(
    name: str = typer.Option(
        "Untitled Project",
        "--name",
        "-n",
        help="Project name.",
    ),
    bib: Path | None = typer.Option(
        None,
        "--bib",
        "-b",
        help="Path to BibTeX file to include.",
        exists=True,
        dir_okay=False,
    ),
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to initialize (defaults to current directory).",
    ),
):
    """Initialize a new Papercutter project.

    Creates a .papercutter/ folder with:
    - config.yaml (project configuration)
    - inventory.json (paper tracking)
    - markdown/ (converted papers)
    - chunks/ (split book chapters)

    Example:
        papercutter init --name "My Literature Review" --bib refs.bib
    """
    directory = Path(directory).resolve()

    # Check if project already exists
    project_dir = directory / ".papercutter"
    if project_dir.exists():
        console.print(f"[yellow]Project already exists at {project_dir}[/yellow]")
        raise typer.Abort()

    # Create project
    manager = ProjectManager(directory)
    manager.init_project(name=name, bib_path=bib)

    console.print(f"[green]Created project '{name}'[/green]")
    console.print(f"  [dim]Location: {project_dir}[/dim]")

    if bib:
        console.print(f"  [dim]BibTeX: {bib}[/dim]")

    console.print()
    console.print("Next steps:")
    console.print("  1. Add PDFs to your project directory")
    console.print("  2. Run [bold]papercutter ingest[/bold] to process papers")
    console.print("  3. Run [bold]papercutter configure[/bold] to set up extraction schema")
