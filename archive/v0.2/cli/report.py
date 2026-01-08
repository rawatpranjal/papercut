"""Report command for generating LLM-powered paper summaries."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from papercutter.exceptions import PapercutterError
from papercutter.llm.prompts import list_templates

console = Console()

app = typer.Typer(
    help="Generate LLM-powered reports from academic papers.",
    no_args_is_help=True,
)


def get_output_format(output: Optional[Path]) -> str:
    """Determine output format from file extension."""
    if output is None:
        return "markdown"

    suffix = output.suffix.lower()
    return {
        ".md": "markdown",
        ".json": "json",
        ".tex": "latex",
        ".latex": "latex",
        ".pdf": "pdf",
    }.get(suffix, "markdown")


@app.command("generate")
def generate(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (format inferred from extension: .md, .json, .tex, .pdf)",
    ),
    template: str = typer.Option(
        "reading_group",
        "--template",
        "-t",
        help="Report template (reading_group, meta_analysis, book_chapter, simulation)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model to use (default: claude-sonnet)",
    ),
    output_format: Optional[str] = typer.Option(
        None,
        "--format",
        "-f",
        help="Output format (markdown, json, latex, pdf). Overrides file extension.",
    ),
):
    """Generate a report from an academic paper.

    Examples:

        papercutter report generate paper.pdf

        papercutter report generate paper.pdf -t meta_analysis -o data.json

        papercutter report generate paper.pdf -o summary.pdf
    """
    from papercutter.report.generator import ReportGenerator
    from papercutter.report.renderers import render_json, render_latex, render_markdown
    from papercutter.report.renderers.pdf import render_pdf

    # Validate template
    available_templates = list_templates()
    if template not in available_templates:
        console.print(f"[red]Unknown template:[/red] {template}")
        console.print(f"[dim]Available: {', '.join(available_templates)}[/dim]")
        raise typer.Exit(1)

    # Determine output format
    fmt = output_format or get_output_format(output)

    try:
        with console.status(f"Generating {template} report..."):
            generator = ReportGenerator(model=model)
            report = generator.generate(
                pdf_path=pdf_path,
                template=template,
                output_format=fmt if fmt != "pdf" else "markdown",
            )

        # Render to appropriate format
        if fmt == "json":
            rendered = render_json(report)
        elif fmt == "latex":
            rendered = render_latex(report)
        elif fmt == "pdf":
            if output is None:
                output = pdf_path.with_suffix(".pdf").with_stem(pdf_path.stem + "_summary")
            render_pdf(report, output)
            console.print(f"[green]PDF saved:[/green] {output}")
            return
        else:
            rendered = render_markdown(report)

        if output:
            output.write_text(rendered)
            console.print(f"[green]Saved:[/green] {output}")
        else:
            console.print(Panel(rendered, title=f"{template} report", border_style="blue"))

    except PapercutterError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise typer.Exit(e.exit_code)


@app.command("templates")
def templates():
    """List available report templates."""
    from papercutter.llm.prompts import TEMPLATES

    console.print("\n[bold]Available Templates[/bold]\n")

    for name, tmpl in TEMPLATES.items():
        console.print(f"  [cyan]{name}[/cyan]")
        console.print(f"    {tmpl.description}")
        console.print()
