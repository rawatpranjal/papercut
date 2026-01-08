"""Simulation commands for generating code from papers."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from papercut.exceptions import PapercutError

console = Console()

app = typer.Typer(
    help="Generate simulation code from paper models.",
    no_args_is_help=True,
)


@app.command("generate")
def generate(
    pdf_path: Path = typer.Argument(..., help="Path to paper PDF"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
    language: str = typer.Option(
        "python",
        "--language",
        "-l",
        help="Target language: python or r",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model to use",
    ),
    both: bool = typer.Option(
        False,
        "--both",
        "-b",
        help="Generate both Python and R versions",
    ),
):
    """Generate simulation code from a paper's model.

    Extracts the theoretical/empirical model from the paper and
    generates runnable simulation code.

    Examples:

        papercut simulate generate paper.pdf

        papercut simulate generate paper.pdf -l r -o model.R

        papercut simulate generate paper.pdf --both -o output_dir/
    """
    from papercut.codegen.generator import SimulationGenerator

    # Validate language
    language = language.lower()
    if language not in ("python", "r"):
        console.print(f"[red]Invalid language:[/red] {language}")
        console.print("[dim]Supported: python, r[/dim]")
        raise typer.Exit(1)

    try:
        generator = SimulationGenerator(model=model)

        if both:
            # Generate both versions
            with console.status("Generating Python code..."):
                py_code = generator.generate(pdf_path, language="python")

            with console.status("Generating R code..."):
                r_code = generator.generate(pdf_path, language="r")

            if output:
                # Output is a directory
                output.mkdir(parents=True, exist_ok=True)
                py_path = output / py_code.default_filename()
                r_path = output / r_code.default_filename()

                py_code.save(py_path)
                r_code.save(r_path)

                console.print(f"[green]Saved:[/green] {py_path}")
                console.print(f"[green]Saved:[/green] {r_path}")
            else:
                # Display both
                console.print(Panel(
                    Syntax(py_code.code, "python", theme="monokai"),
                    title="Python",
                    border_style="blue",
                ))
                console.print()
                console.print(Panel(
                    Syntax(r_code.code, "r", theme="monokai"),
                    title="R",
                    border_style="green",
                ))

        else:
            # Generate single version
            with console.status(f"Generating {language.capitalize()} code..."):
                code = generator.generate(pdf_path, language=language)

            if output:
                code.save(output)
                console.print(f"[green]Saved:[/green] {output}")
            else:
                syntax = Syntax(
                    code.code,
                    language if language != "r" else "r",
                    theme="monokai",
                    line_numbers=True,
                )
                console.print(Panel(
                    syntax,
                    title=f"{language.capitalize()} Simulation",
                    border_style="blue",
                ))

    except PapercutError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise typer.Exit(e.exit_code)


@app.command("languages")
def languages():
    """List supported programming languages."""
    console.print("\n[bold]Supported Languages[/bold]\n")
    console.print("  [cyan]python[/cyan] - Python 3.x with NumPy/SciPy")
    console.print("  [cyan]r[/cyan]      - R with tidyverse")
    console.print()
    console.print("[dim]Use --both to generate both versions[/dim]")
