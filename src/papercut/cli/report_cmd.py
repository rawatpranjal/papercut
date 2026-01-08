"""Report command for LLM-powered structured reports."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from papercut.output import get_formatter

console = Console()


def report(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    template: str = typer.Option(
        "reading-group",
        "--template",
        "-t",
        help="Report template: reading-group, referee, meta, executive, or path to custom template",
    ),
    output: Optional[Path] = typer.Option(
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
    """Generate a structured report about a paper using LLM.

    Built-in templates:
    - reading-group: Discussion questions and key points
    - referee: Reviewer/referee report format
    - meta: Data extraction for meta-analysis
    - executive: Non-technical summary

    Requires an API key (set PAPERCUT_API_KEY or ANTHROPIC_API_KEY).

    Examples:

        papercut report paper.pdf

        papercut report paper.pdf --template referee

        papercut report paper.pdf --template my-template.md
    """
    from papercut.intelligence.report import BUILTIN_TEMPLATES, ReportGenerator
    from papercut.llm.client import LLMNotAvailableError

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty)

    try:
        generator = ReportGenerator()

        if not generator.is_available():
            result = {
                "success": False,
                "error": "LLM not available. Set PAPERCUT_API_KEY or ANTHROPIC_API_KEY.",
            }
            formatter.output(result)
            raise typer.Exit(1)

        # Check if template is a file path or built-in
        custom_template = None
        template_path = Path(template)
        if template_path.exists():
            custom_template = template_path
            template_name = template_path.stem
        elif template not in BUILTIN_TEMPLATES:
            console.print(f"[red]Unknown template:[/red] {template}")
            console.print(f"[dim]Built-in templates: {', '.join(BUILTIN_TEMPLATES)}[/dim]")
            console.print("[dim]Or provide a path to a custom template file[/dim]")
            raise typer.Exit(1)
        else:
            template_name = template

        console.print(f"[dim]Generating {template_name} report for {pdf_path.name}...[/dim]", err=True)

        report_obj = generator.generate(
            pdf_path=pdf_path,
            template=template_name,
            custom_template=custom_template,
        )

        result = {
            "success": True,
            "file": str(pdf_path.name),
            **report_obj.to_dict(),
        }

        if output:
            output.write_text(report_obj.content)
            console.print(f"[green]Saved:[/green] {output}")
        else:
            # For pretty output, render as markdown
            if not formatter.use_json:
                console.print()
                console.print(Markdown(report_obj.content))
                console.print()
                console.print(
                    f"[dim]Model: {report_obj.model} | "
                    f"Tokens: {report_obj.input_tokens} in, {report_obj.output_tokens} out[/dim]"
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
    except Exception as e:
        result = {"success": False, "error": str(e)}
        formatter.output(result)
        raise typer.Exit(1)
