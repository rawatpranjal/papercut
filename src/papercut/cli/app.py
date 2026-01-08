"""Main Typer application for Papercut CLI."""

import functools
from typing import Optional

import typer
from rich.console import Console

from papercut import __version__
from papercut.cli import (
    cache_cmd,
    extract,
    fetch,
    index_cmd,
    read_cmd,
    report_cmd,
    study_cmd,
    summarize_cmd,
)
from papercut.exceptions import PapercutError

console = Console(stderr=True)

app = typer.Typer(
    name="papercut",
    help="Extract and map content from academic papers.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Add subcommand groups
app.add_typer(fetch.app, name="fetch")
app.add_typer(extract.app, name="extract")

# Add direct commands - Layer 1 (extraction)
app.command("index")(index_cmd.index)
app.command("chapters")(index_cmd.chapters)
app.command("info")(index_cmd.info)
app.command("read")(read_cmd.read)
app.command("clear-cache")(cache_cmd.clear_cache)
app.command("cache-info")(cache_cmd.cache_info)

# Add direct commands - Layer 2 (intelligence/LLM)
app.command("summarize")(summarize_cmd.summarize)
app.command("report")(report_cmd.report)
app.command("study")(study_cmd.study)


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
    """Papercut: Extract and map content from academic papers."""
    pass


if __name__ == "__main__":
    app()
