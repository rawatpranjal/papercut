"""Follow references command - download cited papers."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from papercutter.cli.utils import handle_errors, is_quiet
from papercutter.output import get_formatter

console = Console()


def follow(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Path = typer.Option(
        Path("./cited_papers"),
        "--output",
        "-o",
        help="Output directory for downloaded papers",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be downloaded without fetching",
    ),
    parallel: int = typer.Option(
        1,
        "--parallel",
        "-j",
        help="Number of concurrent downloads (1 = sequential)",
    ),
    continue_on_error: bool = typer.Option(
        True,
        "--continue-on-error/--stop-on-error",
        help="Continue downloading after failures",
    ),
    rate_limit: float = typer.Option(
        1.0,
        "--rate-limit",
        help="Delay between downloads in seconds",
    ),
    save_manifest: bool = typer.Option(
        True,
        "--manifest/--no-manifest",
        help="Save manifest.json with resolution details",
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
    """Follow and download referenced papers.

    Extracts references from a PDF, resolves them to downloadable
    sources (arXiv, DOI, URL), and downloads the papers.

    Examples:

        papercutter follow paper.pdf

        papercutter follow paper.pdf -o ./library/

        papercutter follow paper.pdf --dry-run

        papercutter follow paper.pdf --parallel 3 --rate-limit 2.0
    """
    from papercutter.core.follower import FollowProgress, FollowResult, ReferenceFollower
    from papercutter.core.references import ReferenceExtractor
    from papercutter.core.resolver import ReferenceResolver
    from papercutter.extractors.pdfplumber import PdfPlumberExtractor
    from papercutter.fetchers.registry import get_registry

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())
    quiet_mode = is_quiet()

    # Validate parameters
    if parallel < 1:
        console.print("[red]Error:[/red] --parallel must be at least 1")
        raise typer.Exit(1)
    if rate_limit < 0:
        console.print("[red]Error:[/red] --rate-limit must be non-negative")
        raise typer.Exit(1)

    # Extract references
    if not quiet_mode:
        console.print(f"[dim]Extracting references from {pdf_path.name}...[/dim]")

    ref_extractor = ReferenceExtractor(PdfPlumberExtractor())
    references = ref_extractor.extract(pdf_path)

    if not references:
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "message": "No references found in document",
            "total_references": 0,
        }
        formatter.output(result)
        return

    if not quiet_mode:
        console.print(f"[bold]Found {len(references)} references[/bold]")

    # Resolve references
    registry = get_registry()
    resolver = ReferenceResolver(registry)
    resolved_refs = resolver.resolve_all(references, deduplicate=True)

    resolved_count = len([r for r in resolved_refs if r.is_resolved])
    unresolved_count = len([r for r in resolved_refs if not r.is_resolved])

    # Group by source type
    by_source: dict[str, int] = {}
    for ref in resolved_refs:
        if ref.is_resolved:
            source = ref.source_type or "unknown"
            by_source[source] = by_source.get(source, 0) + 1

    if not quiet_mode:
        console.print(f"[green]Resolved {resolved_count}[/green] to downloadable sources:")
        for source, count in sorted(by_source.items()):
            console.print(f"  - {count} {source}")
        if unresolved_count > 0:
            console.print(f"[yellow]{unresolved_count} could not be resolved[/yellow]")

    # Dry run mode
    if dry_run:
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "dry_run": True,
            "total_references": len(references),
            "resolved": resolved_count,
            "unresolved": unresolved_count,
            "by_source": by_source,
            "would_download": [
                {"id": r.resolved_id, "source": r.source_type}
                for r in resolved_refs
                if r.is_resolved
            ],
        }
        formatter.output(result)
        return

    if resolved_count == 0:
        result = {
            "success": True,
            "file": str(pdf_path.name),
            "message": "No references could be resolved to downloadable sources",
            "total_references": len(references),
            "resolved": 0,
            "unresolved": unresolved_count,
        }
        formatter.output(result)
        return

    # Download
    if not quiet_mode:
        console.print(f"\n[bold]Downloading to {output}...[/bold]")

    follower = ReferenceFollower(
        registry=registry,
        max_parallel=parallel,
        continue_on_error=continue_on_error,
        rate_limit_delay=rate_limit,
    )

    def progress_callback(progress: FollowProgress):
        if not quiet_mode and not formatter.use_json:
            console.print(
                f"[dim]Progress: {progress.downloaded}/{progress.resolved} downloaded, "
                f"{progress.failed} failed[/dim]",
                end="\r",
            )

    # Extract and follow
    follow_result = follower.follow(
        pdf_path,
        output,
        dry_run=False,
        progress_callback=progress_callback if not formatter.use_json else None,
    )

    # Clear progress line
    if not quiet_mode and not formatter.use_json:
        console.print(" " * 60, end="\r")

    # Write manifest and unresolved
    if save_manifest:
        manifest = follower.generate_manifest(pdf_path, follow_result, resolved_refs)
        follower.write_manifest(output, manifest)

        if follow_result.unresolved:
            follower.write_unresolved(output, pdf_path, follow_result.unresolved)

    # Report results
    if not quiet_mode and not formatter.use_json:
        console.print(f"\n[bold]Done:[/bold]")
        console.print(f"  [green]{len(follow_result.downloaded)} downloaded[/green]")
        if follow_result.failed:
            console.print(f"  [red]{len(follow_result.failed)} failed[/red]")
        if follow_result.unresolved:
            console.print(f"  [yellow]{len(follow_result.unresolved)} unresolved[/yellow]")
        if save_manifest:
            console.print(f"\n[dim]Manifest: {output}/_manifest.json[/dim]")

    # JSON output
    result = {
        "success": True,
        "file": str(pdf_path.name),
        "output_dir": str(output),
        "total_references": follow_result.total_references,
        "downloaded": len(follow_result.downloaded),
        "failed": len(follow_result.failed),
        "unresolved": len(follow_result.unresolved),
        "by_source": by_source,
        "downloaded_files": [str(d.path.name) for d in follow_result.downloaded],
    }

    if follow_result.failed:
        result["failed_refs"] = [
            {"id": r.resolved_id, "error": e[:100]}
            for r, e in follow_result.failed
        ]

    if formatter.use_json:
        formatter.output(result)
