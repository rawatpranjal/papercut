"""Main Typer application for Papercutter CLI."""

import os
from typing import Optional

import certifi
import typer
from rich.console import Console

from papercutter import __version__
from papercutter.cli.utils import handle_errors, set_context

# Ensure SSL certificates are properly configured for macOS compatibility
# This is needed for third-party libraries (like arxiv) that use requests/urllib
if "SSL_CERT_FILE" not in os.environ:
    os.environ["SSL_CERT_FILE"] = certifi.where()

# Default console for output
console = Console(stderr=True)

app = typer.Typer(
    name="papercutter",
    help="Extract and map content from academic papers.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"papercutter version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed error messages with full tracebacks.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress status output; still shows errors.",
    ),
    silent: bool = typer.Option(
        False,
        "--silent",
        help="Completely silent (exit code only).",
    ),
):
    """Papercutter: Extract and map content from academic papers."""
    # Store flags in context for subcommands
    ctx.ensure_object(dict)
    quiet_level = 2 if silent else 1 if quiet else 0
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet_level

    # Also set global context for modules that can't access typer context
    set_context(verbose=verbose, quiet=quiet_level)


def _wrap_command(func):
    """Wrap a command function with error handling."""
    return handle_errors(func)


def _setup_commands():
    """Set up all commands after imports are resolved."""
    # Import here to avoid circular imports
    from papercutter.cli import (
        cache_cmd,
        equations_cmd,
        extract,
        fetch,
        follow_cmd,
        index_cmd,
        read_cmd,
        report_cmd,
        search_cmd,
        study_cmd,
        summarize_cmd,
    )

    # Add subcommand groups
    app.add_typer(fetch.app, name="fetch")
    app.add_typer(extract.app, name="extract")

    # Register direct commands with error handling
    # Layer 1 (extraction)
    app.command("index")(_wrap_command(index_cmd.index))
    app.command("chapters")(_wrap_command(index_cmd.chapters))
    app.command("info")(_wrap_command(index_cmd.info))
    app.command("read")(_wrap_command(read_cmd.read))
    app.command("clear-cache")(_wrap_command(cache_cmd.clear_cache))
    app.command("cache-info")(_wrap_command(cache_cmd.cache_info))
    app.command("follow")(_wrap_command(follow_cmd.follow))
    app.command("equations")(_wrap_command(equations_cmd.equations))
    app.command("equation")(_wrap_command(equations_cmd.equation))
    app.command("search")(_wrap_command(search_cmd.search))

    # Layer 2 (intelligence/LLM)
    app.command("summarize")(_wrap_command(summarize_cmd.summarize))
    app.command("report")(_wrap_command(report_cmd.report))
    app.command("study")(_wrap_command(study_cmd.study))


# Setup commands
_setup_commands()


if __name__ == "__main__":
    app()
