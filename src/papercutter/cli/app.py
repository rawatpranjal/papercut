"""Main Typer application for Papercutter Factory CLI."""

import logging
import os

import certifi
import typer
from rich.console import Console

from papercutter import __version__
from papercutter.cli.utils import handle_errors, set_context

# Ensure SSL certificates are properly configured for macOS compatibility
# This is needed for third-party libraries (like arxiv) that use requests/urllib
if "SSL_CERT_FILE" not in os.environ:
    os.environ["SSL_CERT_FILE"] = certifi.where()


# Deduplicate pypdf warnings (e.g., "Rotated text discovered" shown per-page)
class _OnceFilter(logging.Filter):
    """Logging filter that only shows each unique message once."""

    def __init__(self):
        super().__init__()
        self.seen: set[str] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if msg in self.seen:
            return False
        self.seen.add(msg)
        return True


# Apply the filter to pypdf logger to avoid warning spam
logging.getLogger("pypdf").addFilter(_OnceFilter())

# Default console for output
console = Console(stderr=True)

app = typer.Typer(
    name="papercutter",
    help="""Papercutter Factory: Automated Evidence Synthesis Pipeline

    [bold]Workflow:[/bold]
    init        Initialize a new review project
    ingest      Process PDFs (split volumes, match BibTeX, convert to Markdown)
    configure   Define extraction schema (auto-generated with LLM)
    grind       Extract structured evidence from papers
    report      Generate LaTeX/Markdown systematic review document
    status      Show project processing status
    """,
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
    version: bool | None = typer.Option(
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
    """Papercutter Factory: Automated evidence synthesis for systematic reviews."""
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
    # Import Factory pipeline commands
    from papercutter.cli import (
        configure_cmd,
        factory_report_cmd,
        grind_cmd,
        ingest_cmd,
        init_cmd,
        status_cmd,
    )

    # Factory pipeline commands
    app.command("init")(_wrap_command(init_cmd.init))
    app.command("ingest")(_wrap_command(ingest_cmd.ingest))
    app.command("configure")(_wrap_command(configure_cmd.configure))
    app.command("grind")(_wrap_command(grind_cmd.grind))
    app.command("report")(_wrap_command(factory_report_cmd.report))
    app.command("status")(_wrap_command(status_cmd.status))


# Setup commands
_setup_commands()


if __name__ == "__main__":
    app()
