"""Study command for LLM-powered study aids."""

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

from papercutter.output import get_formatter

console = Console()


def study(
    pdf_path: Path = typer.Argument(..., help="Path to book PDF file"),
    chapter: int | None = typer.Option(
        None,
        "--chapter",
        "-c",
        help="Chapter ID to study (run 'papercutter chapters' first)",
    ),
    mode: str = typer.Option(
        "summary",
        "--mode",
        "-m",
        help="Study mode: summary, concepts, quiz, flashcards",
    ),
    pages: str | None = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range if not using chapter (e.g., '50-75')",
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
        help="Force pretty output (markdown)",
    ),
):
    """Generate study materials from a book chapter using LLM.

    Study modes:
    - summary: Chapter overview and key points
    - concepts: Key concepts with definitions
    - quiz: Practice questions at different levels
    - flashcards: Flashcard-format study cards

    Requires an API key (set PAPERCUTTER_API_KEY or ANTHROPIC_API_KEY).

    Examples:

        papercutter study book.pdf --chapter 5

        papercutter study book.pdf --chapter 3 --mode quiz

        papercutter study book.pdf --pages 50-75 --mode flashcards
    """
    from papercutter.cli.extract import parse_pages
    from papercutter.intelligence.study import STUDY_MODES, StudyAid
    from papercutter.llm.client import LLMNotAvailableError

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)

    try:
        study_aid = StudyAid()

        if not study_aid.is_available():
            result = {
                "success": False,
                "error": "LLM not available. Set PAPERCUTTER_API_KEY or ANTHROPIC_API_KEY.",
            }
            formatter.output(result)
            raise typer.Exit(1)

        # Validate mode
        if mode not in STUDY_MODES:
            console.print(f"[red]Unknown mode:[/red] {mode}")
            console.print(f"[dim]Valid modes: {', '.join(STUDY_MODES)}[/dim]")
            raise typer.Exit(1)

        # Need either chapter or pages
        if chapter is None and pages is None:
            console.print("[red]Specify --chapter or --pages[/red]")
            console.print("[dim]Run 'papercutter chapters book.pdf' to see available chapters[/dim]")
            raise typer.Exit(1)

        # Parse pages if provided
        page_list = None
        if pages:
            page_list = parse_pages(pages)

        desc = f"chapter {chapter}" if chapter else f"pages {pages}"
        console.print(f"[dim]Generating {mode} materials for {desc}...[/dim]", err=True)

        material = study_aid.generate(
            pdf_path=pdf_path,
            mode=mode,
            chapter=chapter,
            pages=page_list,
        )

        result = {
            "success": True,
            "file": str(pdf_path.name),
            **material.to_dict(),
        }

        if output:
            output.write_text(material.content)
            console.print(f"[green]Saved:[/green] {output}")
        else:
            # For pretty output, render as markdown
            if not formatter.use_json:
                console.print()
                console.print(Markdown(material.content))
                console.print()
                console.print(
                    f"[dim]Model: {material.model} | "
                    f"Tokens: {material.input_tokens} in, {material.output_tokens} out[/dim]"
                )
            else:
                formatter.output(result)

    except LLMNotAvailableError as e:
        result = {"success": False, "error": str(e)}
        formatter.output(result)
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print(f"[red]File not found:[/red] {pdf_path}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        result = {"success": False, "error": str(e)}
        formatter.output(result)
        raise typer.Exit(1)
