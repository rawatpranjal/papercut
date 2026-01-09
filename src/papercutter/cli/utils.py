"""Shared utilities for CLI commands."""

import functools
import io
from collections.abc import Callable
from typing import Any, TypeVar

import typer
from rich.console import Console

from papercutter.exceptions import PapercutterError

# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])

# Default console for error output (stderr)
_error_console = Console(stderr=True)

# Context storage for flags
_context: dict[str, Any] = {"verbose": False, "quiet": 0}


def set_context(verbose: bool = False, quiet: int = 0) -> None:
    """Set global context values."""
    _context["verbose"] = verbose
    _context["quiet"] = quiet


def get_context_value(key: str, default: Any = None) -> Any:
    """Get a value from the context."""
    return _context.get(key, default)


def get_console() -> Console:
    """Get a Console instance respecting quiet mode.

    Returns a null console when quiet mode is enabled.
    """
    if is_quiet():
        return Console(file=io.StringIO(), stderr=True)
    return Console(stderr=True)


def is_quiet() -> bool:
    """Check if quiet mode is enabled (-q or -qq)."""
    quiet_val = get_context_value("quiet", 0)
    # Handle both bool and int
    if isinstance(quiet_val, bool):
        return quiet_val
    return bool(quiet_val >= 1)


def is_silent() -> bool:
    """Check if silent mode is enabled (-qq).

    In silent mode, even errors are suppressed (exit code only).
    """
    quiet_val = get_context_value("quiet", 0)
    if isinstance(quiet_val, bool):
        return False
    return bool(quiet_val >= 2)


def is_verbose() -> bool:
    """Check if verbose mode is enabled (-v)."""
    return bool(get_context_value("verbose", False))


def handle_errors(func: F) -> F:
    """Decorator for consistent CLI error handling.

    Catches common exceptions and displays user-friendly error messages
    instead of raw Python tracebacks. Respects --verbose and --quiet flags.

    Quiet levels:
    - -q: Suppress status messages, show errors with hints
    - -qq: Silent mode, suppress everything (exit code only)
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        err_console = get_console()
        verbose = is_verbose()
        silent = is_silent()

        try:
            return func(*args, **kwargs)
        except PapercutterError as e:
            if not silent:
                if verbose:
                    err_console.print_exception()
                else:
                    err_console.print(f"[red]Error:[/red] {e.message}")
                    if e.details:
                        err_console.print(f"[dim]{e.details}[/dim]")
                    if e.hint:
                        err_console.print(f"[dim]Hint: {e.hint}[/dim]")
            raise typer.Exit(e.exit_code)
        except FileNotFoundError as e:
            if not silent:
                if verbose:
                    err_console.print_exception()
                else:
                    filename = getattr(e, "filename", None) or str(e)
                    err_console.print(f"[red]File not found:[/red] {filename}")
            raise typer.Exit(1)
        except PermissionError as e:
            if not silent:
                if verbose:
                    err_console.print_exception()
                else:
                    filename = getattr(e, "filename", None) or str(e)
                    err_console.print(f"[red]Permission denied:[/red] {filename}")
            raise typer.Exit(1)
        except IsADirectoryError as e:
            if not silent:
                if verbose:
                    err_console.print_exception()
                else:
                    filename = getattr(e, "filename", None) or str(e)
                    err_console.print(f"[red]Expected file, got directory:[/red] {filename}")
            raise typer.Exit(1)
        except KeyboardInterrupt:
            if not silent:
                err_console.print("\n[yellow]Interrupted[/yellow]")
            raise typer.Exit(130)
        except typer.Exit:
            # Re-raise typer exits (already handled)
            raise
        except typer.BadParameter:
            # Re-raise bad parameter errors
            raise
        except Exception as e:
            if not silent:
                if verbose:
                    err_console.print_exception()
                else:
                    err_console.print(f"[red]Unexpected error:[/red] {type(e).__name__}: {e}")
            raise typer.Exit(1)

    return wrapper  # type: ignore[return-value]
