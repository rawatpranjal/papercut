"""Search commands for finding papers."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from papercutter.cli.utils import handle_errors, is_quiet
from papercutter.output import get_formatter

console = Console()


def search(
    query: str = typer.Argument(..., help="Search query"),
    source: str = typer.Option(
        "arxiv",
        "--source",
        "-s",
        help="Search source (arxiv).",
    ),
    author: Optional[str] = typer.Option(
        None,
        "--author",
        "-a",
        help="Filter by author name.",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results.",
    ),
    year: Optional[int] = typer.Option(
        None,
        "--year",
        "-y",
        help="Filter by publication year.",
    ),
    use_json: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON.",
    ),
    fetch: bool = typer.Option(
        False,
        "--fetch",
        "-f",
        help="Interactively select and download a paper.",
    ),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for downloaded PDF (with --fetch).",
    ),
):
    """Search for academic papers.

    Search arXiv for papers matching your query. Use filters to narrow results.

    Examples:

    \b
        papercutter search "transformer attention"
        papercutter search "machine learning" --author "Hinton" --limit 5
        papercutter search "neural networks" --year 2023
        papercutter search "attention" --fetch -o ./papers/
    """
    formatter = get_formatter(json_flag=use_json, quiet=is_quiet())
    quiet_mode = is_quiet()

    if source.lower() != "arxiv":
        console.print(f"[red]Error:[/red] Unsupported search source: {source}")
        console.print("[dim]Currently supported: arxiv[/dim]")
        raise typer.Exit(1)

    # Search arXiv
    results = _search_arxiv(query, author=author, year=year, limit=limit)

    if not results:
        if not quiet_mode:
            console.print("[yellow]No results found[/yellow]")
        if formatter.use_json:
            formatter.output({"query": query, "results": []})
        return

    # JSON output
    if formatter.use_json:
        formatter.output({
            "query": query,
            "source": source,
            "count": len(results),
            "results": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "authors": r["authors"],
                    "published": r["published"],
                    "abstract": r["abstract"][:300] + "..." if len(r["abstract"]) > 300 else r["abstract"],
                }
                for r in results
            ],
        })
        return

    # Pretty output
    if not quiet_mode:
        console.print(f"\n[bold]Found {len(results)} result(s):[/bold]\n")

    for i, result in enumerate(results, 1):
        _print_result(i, result)

    # Interactive fetch mode
    if fetch:
        console.print()
        choice = typer.prompt(
            "Enter number to download (or press Enter to skip)",
            default="",
            show_default=False,
        )

        if choice.strip():
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    selected = results[idx]
                    _fetch_selected(selected, output)
                else:
                    console.print("[red]Invalid selection[/red]")
            except ValueError:
                console.print("[red]Invalid number[/red]")


def _search_arxiv(
    query: str,
    author: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 10,
) -> list[dict]:
    """Search arXiv for papers.

    Args:
        query: Search query.
        author: Optional author filter.
        year: Optional year filter.
        limit: Maximum results.

    Returns:
        List of result dictionaries.
    """
    try:
        import arxiv
    except ImportError:
        console.print("[red]Error:[/red] arxiv library not installed")
        console.print("[dim]Install with: pip install arxiv[/dim]")
        raise typer.Exit(1)

    # Build search query
    search_query = query
    if author:
        search_query = f'au:"{author}" AND ({query})'

    # Create search
    client = arxiv.Client()
    search = arxiv.Search(
        query=search_query,
        max_results=limit * 2 if year else limit,  # Over-fetch if filtering by year
        sort_by=arxiv.SortCriterion.Relevance,
    )

    results = []
    for paper in client.results(search):
        # Year filter
        if year and paper.published.year != year:
            continue

        results.append({
            "id": paper.entry_id.split("/")[-1],
            "title": paper.title.replace("\n", " "),
            "authors": [a.name for a in paper.authors],
            "published": paper.published.strftime("%Y-%m-%d"),
            "abstract": paper.summary.replace("\n", " "),
            "categories": paper.categories,
            "pdf_url": paper.pdf_url,
        })

        if len(results) >= limit:
            break

    return results


def _print_result(index: int, result: dict) -> None:
    """Print a single search result."""
    console.print(f"[bold cyan]{index}.[/bold cyan] [bold]{result['title']}[/bold]")
    authors_str = ", ".join(result["authors"][:3])
    if len(result["authors"]) > 3:
        authors_str += f" et al. ({len(result['authors'])} authors)"
    console.print(f"   [dim]{authors_str}[/dim]")
    console.print(f"   [green]arXiv:{result['id']}[/green] | {result['published']}")

    # Truncated abstract
    abstract = result["abstract"]
    if len(abstract) > 200:
        abstract = abstract[:200] + "..."
    console.print(f"   [dim]{abstract}[/dim]")
    console.print()


def _fetch_selected(result: dict, output: Path) -> None:
    """Fetch the selected paper."""
    from papercutter.fetchers.arxiv import ArxivFetcher

    arxiv_id = result["id"]
    console.print(f"\n[dim]Downloading arXiv:{arxiv_id}...[/dim]")

    try:
        fetcher = ArxivFetcher()
        doc = fetcher.fetch(arxiv_id, output)
        console.print(f"[green]Downloaded:[/green] {doc.path}")
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
