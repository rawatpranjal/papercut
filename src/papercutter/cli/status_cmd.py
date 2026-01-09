"""Status command for Papercutter Factory.

Shows the current state of a project.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from papercutter.project.inventory import PaperStatus
from papercutter.project.manager import ProjectManager

console = Console()


def status(
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
        help="Show detailed paper list.",
    ),
):
    """Show project status.

    Displays:
    - Project configuration
    - Paper inventory status
    - Extraction progress

    Example:
        papercutter status
        papercutter status -v  # Show paper list
    """
    directory = Path(directory).resolve()
    manager = ProjectManager(directory)

    # Check if project exists
    if not manager.exists():
        console.print("[yellow]No project found in this directory.[/yellow]")
        console.print("Run 'papercutter init' to create a project.")
        raise typer.Exit(1)

    # Load project
    manager.load()

    # Header
    console.print(f"[bold]Project: {manager.config.name}[/bold]")
    console.print(f"  Location: {manager.project_dir}")
    if manager.config.bibtex_path:
        console.print(f"  BibTeX: {manager.config.bibtex_path}")
    console.print()

    # Inventory status
    entries = list(manager.inventory.papers.values())
    if not entries:
        console.print("[yellow]No papers in inventory.[/yellow]")
        console.print("Run 'papercutter ingest <path>' to add papers.")
        return

    # Count by status
    status_counts = {s: 0 for s in PaperStatus}
    for entry in entries:
        status_counts[entry.status] += 1

    console.print("[bold]Inventory:[/bold]")
    console.print(f"  Total papers: {len(entries)}")
    console.print(f"  Pending: {status_counts[PaperStatus.PENDING]}")
    console.print(f"  Ingested: {status_counts[PaperStatus.INGESTED]}")
    console.print(f"  Failed: {status_counts[PaperStatus.FAILED]}")

    # Count with BibTeX match
    with_bibtex = sum(1 for e in entries if e.bibtex_key)
    console.print(f"  With BibTeX: {with_bibtex}")

    # Count split books
    split_children = sum(1 for e in entries if e.is_split_child)
    if split_children:
        console.print(f"  Split chapters: {split_children}")

    console.print()

    # Extraction status
    matrix_path = manager.project_dir / "matrix.json"
    if matrix_path.exists():
        console.print("[bold]Extraction:[/bold]")
        try:
            from papercutter.grinding import ExtractionMatrix

            matrix = ExtractionMatrix.from_json(matrix_path)
            console.print(f"  Papers extracted: {matrix.paper_count}")
            console.print(f"  Fields: {len(matrix.field_keys)}")

            with_summary = sum(1 for p in matrix if p.one_pager)
            console.print(f"  With summaries: {with_summary}")
        except Exception as e:
            console.print(f"  [yellow]Error loading matrix: {e}[/yellow]")
    else:
        console.print("[dim]No extraction matrix. Run 'papercutter grind'.[/dim]")

    console.print()

    # Schema status
    if manager.config.grinding.columns:
        console.print("[bold]Schema:[/bold]")
        console.print(f"  Fields configured: {len(manager.config.grinding.columns)}")
        for col in manager.config.grinding.columns[:5]:
            console.print(f"    - {col.key}: {col.type}")
        if len(manager.config.grinding.columns) > 5:
            console.print(f"    ... and {len(manager.config.grinding.columns) - 5} more")
    else:
        console.print("[dim]No schema configured. Run 'papercutter configure'.[/dim]")

    # Verbose: show paper list
    if verbose:
        console.print()
        _show_paper_list(entries)


def _show_paper_list(entries: list) -> None:
    """Show detailed paper list."""
    table = Table(title="Papers")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Title", max_width=40)
    table.add_column("BibTeX Key")
    table.add_column("Status")
    table.add_column("Method")

    for entry in entries[:50]:  # Limit to 50
        status_style = {
            PaperStatus.PENDING: "yellow",
            PaperStatus.INGESTED: "green",
            PaperStatus.FAILED: "red",
        }.get(entry.status, "")

        table.add_row(
            entry.id[:12] + "...",
            (entry.title[:37] + "...") if entry.title and len(entry.title) > 40 else (entry.title or "-"),
            entry.bibtex_key or "-",
            f"[{status_style}]{entry.status.value}[/{status_style}]",
            entry.extraction_method or "-",
        )

    if len(entries) > 50:
        table.add_row("...", f"({len(entries) - 50} more)", "", "", "")

    console.print(table)
