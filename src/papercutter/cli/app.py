"""Main Typer application for Papercutter CLI."""

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
    help="""Papercutter: The Evidence Factory for systematic literature reviews.

    [bold]Pipeline Commands:[/bold]
    init        Initialize a new project
    ingest      Process PDFs (split, match BibTeX, convert to Markdown)
    configure   Set up extraction schema (auto-generated with LLM)
    grind       Extract structured evidence from papers
    factory-report  Generate LaTeX/Markdown review document
    status      Show project status

    [bold]Legacy Commands:[/bold]
    fetch       Download papers from arXiv, DOI, SSRN, NBER
    extract     Extract text, tables, figures, references
    summarize   LLM-powered summarization
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

    # NEW: Factory pipeline commands
    from papercutter.cli import (
        init_cmd,
        ingest_cmd,
        configure_cmd,
        grind_cmd,
        factory_report_cmd,
        status_cmd,
    )

    # Factory pipeline commands (new 5-command architecture)
    app.command("init")(_wrap_command(init_cmd.init))
    app.command("ingest")(_wrap_command(ingest_cmd.ingest))
    app.command("configure")(_wrap_command(configure_cmd.configure))
    app.command("grind")(_wrap_command(grind_cmd.grind))
    app.command("status")(_wrap_command(status_cmd.status))

    # Add subcommand groups (legacy)
    app.add_typer(fetch.app, name="fetch")
    app.add_typer(extract.app, name="extract")

    # Register direct commands with error handling
    # Layer 1 (extraction) - legacy
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

    # Layer 2 (intelligence/LLM) - legacy
    app.command("summarize")(_wrap_command(summarize_cmd.summarize))
    app.command("report")(_wrap_command(report_cmd.report))
    app.command("study")(_wrap_command(study_cmd.study))

    # NEW: Factory report (as 'factory-report' to avoid conflict with legacy)
    app.command("factory-report")(_wrap_command(factory_report_cmd.report))


# Setup commands
_setup_commands()


if __name__ == "__main__":
    app()
