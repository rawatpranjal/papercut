"""Book commands for summarizing book-length PDFs."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from papercutter.exceptions import PapercutterError

console = Console()

app = typer.Typer(
    help="Summarize book-length PDFs chapter by chapter.",
    no_args_is_help=True,
)


@app.command("summarize")
def summarize(
    pdf_path: Path = typer.Argument(..., help="Path to book PDF"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (.md, .json, or .pdf)",
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        "-t",
        help="Book title (auto-detected if not provided)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model to use",
    ),
):
    """Summarize a book by detecting and summarizing each chapter.

    Auto-detects chapters using PDF bookmarks or text patterns,
    then generates summaries for each chapter and a final synthesis.

    Examples:

        papercutter book summarize textbook.pdf

        papercutter book summarize textbook.pdf -o summary.md

        papercutter book summarize textbook.pdf --title "My Textbook" -o summary.pdf
    """
    from papercutter.books.combiner import BookSummarizer
    from papercutter.report.renderers.pdf import render_pdf
    from papercutter.report.generator import Report

    try:
        summarizer = BookSummarizer(model=model)

        # Detect chapters first to show progress
        console.print(f"[dim]Analyzing:[/dim] {pdf_path.name}")
        chapters = summarizer.splitter.detect_chapters(pdf_path)
        console.print(f"[green]Found {len(chapters)} chapter(s)[/green]")

        for i, ch in enumerate(chapters, 1):
            console.print(
                f"  {i}. {ch.title} [dim](pages {ch.start_page + 1}-{ch.end_page})[/dim]"
            )

        console.print()

        # Summarize with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Summarizing chapters...", total=None)

            book_summary = summarizer.summarize(
                pdf_path=pdf_path,
                book_title=title,
                chapters=chapters,
            )

            progress.update(task, description="Complete!")

        # Output
        markdown_content = book_summary.to_markdown()

        if output:
            suffix = output.suffix.lower()

            if suffix == ".pdf":
                # Create a Report object for PDF rendering
                report = Report(
                    content=markdown_content,
                    template="book",
                    output_format="markdown",
                    source_path=pdf_path,
                    metadata={
                        "title": book_summary.title,
                        "chapters": len(book_summary.chapters),
                        "pages": book_summary.total_pages,
                    },
                )
                render_pdf(report, output)
                console.print(f"[green]PDF saved:[/green] {output}")

            elif suffix == ".json":
                import json

                data = {
                    "title": book_summary.title,
                    "source": str(book_summary.source_path),
                    "total_pages": book_summary.total_pages,
                    "synthesis": book_summary.synthesis,
                    "chapters": [
                        {
                            "title": cs.chapter.title,
                            "start_page": cs.chapter.start_page + 1,
                            "end_page": cs.chapter.end_page,
                            "summary": cs.summary,
                        }
                        for cs in book_summary.chapters
                    ],
                }
                output.write_text(json.dumps(data, indent=2))
                console.print(f"[green]JSON saved:[/green] {output}")

            else:
                output.write_text(markdown_content)
                console.print(f"[green]Saved:[/green] {output}")
        else:
            console.print(Panel(markdown_content, title="Book Summary", border_style="blue"))

    except PapercutterError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise typer.Exit(e.exit_code)


@app.command("chapters")
def chapters(
    pdf_path: Path = typer.Argument(..., help="Path to book PDF"),
):
    """Detect and list chapters in a book PDF.

    Uses PDF bookmarks/outline if available, otherwise
    falls back to text pattern detection.

    Example:

        papercutter book chapters textbook.pdf
    """
    from papercutter.books.splitter import ChapterSplitter

    splitter = ChapterSplitter()
    detected = splitter.detect_chapters(pdf_path)

    if not detected:
        console.print("[yellow]No chapters detected[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]Detected {len(detected)} chapter(s)[/bold]\n")

    for i, chapter in enumerate(detected, 1):
        console.print(
            f"  [cyan]{i:2}.[/cyan] {chapter.title}"
        )
        console.print(
            f"      [dim]Pages {chapter.start_page + 1}-{chapter.end_page} "
            f"({chapter.page_count} pages)[/dim]"
        )
        console.print()
