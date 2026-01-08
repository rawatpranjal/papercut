"""Main Typer application for Papercut CLI."""

import functools
from typing import Optional

import typer
from rich.console import Console

from papercut import __version__
from papercut.cli import extract, fetch
from papercut.exceptions import PapercutError

console = Console(stderr=True)

app = typer.Typer(
    name="papercut",
    help="Extract knowledge from academic papers.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Add subcommand groups
app.add_typer(fetch.app, name="fetch")
app.add_typer(extract.app, name="extract")


def handle_errors(func):
    """Decorator for consistent CLI error handling."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PapercutError as e:
            console.print(f"[red]Error:[/red] {e.message}")
            if e.details:
                console.print(f"[dim]{e.details}[/dim]")
            raise typer.Exit(e.exit_code)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            raise typer.Exit(130)

    return wrapper


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"papercut version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
):
    """Papercut: Extract knowledge from academic papers."""
    pass


if __name__ == "__main__":
    app()
