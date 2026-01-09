"""Summarize command for LLM-powered paper summarization."""

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

from papercutter.output import get_formatter

console = Console()


def summarize(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    focus: str | None = typer.Option(
        None,
        "--focus",
        "-f",
        help="Focus area (e.g., methods, results, theory)",
    ),
    length: str = typer.Option(
        "default",
        "--length",
        "-l",
        help="Summary length: short, default, or long",
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
    """Generate an LLM-powered summary of a paper.

    Requires an API key (set ANTHROPIC_API_KEY or OPENAI_API_KEY env var,
    or add to ~/.papercutter/config.yaml).

    Examples:

        papercutter summarize paper.pdf

        papercutter summarize paper.pdf --focus methods

        papercutter summarize paper.pdf --length short
    """
    from papercutter.intelligence.summarize import Summarizer
    from papercutter.llm.client import LLMNotAvailableError

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)

    try:
        summarizer = Summarizer()

        if not summarizer.is_available():
            result = {
                "success": False,
                "error": "LLM not available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY env var, "
                "or add to ~/.papercutter/config.yaml",
            }
            formatter.output(result)
            raise typer.Exit(1)

        # Validate length
        if length not in ("short", "default", "long"):
            console.print(f"[red]Invalid length:[/red] {length}")
            console.print("[dim]Valid options: short, default, long[/dim]")
            raise typer.Exit(1)

        Console(stderr=True).print(f"[dim]Summarizing {pdf_path.name}...[/dim]")

        summary = summarizer.summarize(
            pdf_path=pdf_path,
            focus=focus,
            length=length,
        )

        result = {
            "success": True,
            "file": str(pdf_path.name),
            **summary.to_dict(),
        }

        if output:
            output.write_text(summary.content)
            console.print(f"[green]Saved:[/green] {output}")
        else:
            # For pretty output, render as markdown
            if not formatter.use_json:
                console.print()
                console.print(Markdown(summary.content))
                console.print()
                console.print(
                    f"[dim]Model: {summary.model} | "
                    f"Tokens: {summary.input_tokens} in, {summary.output_tokens} out[/dim]"
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
    except typer.Exit:
        raise
    except Exception as e:
        result = {"success": False, "error": str(e)}
        formatter.output(result)
        raise typer.Exit(1)
