"""Output formatter with JSON/pretty modes and TTY detection."""

import json
import sys
from dataclasses import dataclass
from typing import Any, Optional

from rich.console import Console
from rich.table import Table
from rich.tree import Tree


@dataclass
class OutputFormatter:
    """Handles output formatting with JSON/pretty modes.

    Auto-detects TTY for default mode:
    - TTY (terminal): Pretty formatted output with colors
    - Non-TTY (pipe/redirect): JSON output for machine consumption
    """

    force_json: bool = False
    force_pretty: bool = False
    console: Optional[Console] = None

    def __post_init__(self):
        if self.console is None:
            self.console = Console()

    @property
    def use_json(self) -> bool:
        """Determine if JSON output should be used."""
        if self.force_json:
            return True
        if self.force_pretty:
            return False
        # Auto-detect: JSON if stdout is not a TTY
        return not sys.stdout.isatty()

    def output(self, data: dict[str, Any], pretty_fn: Optional[callable] = None) -> None:
        """Output data in appropriate format.

        Args:
            data: Dictionary to output.
            pretty_fn: Optional function to render pretty output.
                       If not provided, uses default pretty formatter.
        """
        if self.use_json:
            self._output_json(data)
        else:
            if pretty_fn:
                pretty_fn(data, self.console)
            else:
                self._output_pretty_default(data)

    def _output_json(self, data: dict[str, Any]) -> None:
        """Output as JSON."""
        print(json.dumps(data, indent=2))

    def _output_pretty_default(self, data: dict[str, Any]) -> None:
        """Default pretty output using Rich."""
        # Handle common output patterns
        if "success" in data and not data.get("success"):
            self._output_error(data)
        elif "sections" in data:
            self._output_index(data)
        elif "chapters" in data:
            self._output_chapters(data)
        elif "tables" in data:
            self._output_tables(data)
        elif "table" in data:
            self._output_single_table(data)
        elif "figures" in data:
            self._output_figures(data)
        elif "references" in data:
            self._output_references(data)
        elif "content" in data and "text" in data.get("content", {}):
            self._output_text(data)
        else:
            # Fallback to JSON for unknown structures
            self._output_json(data)

    def _output_error(self, data: dict[str, Any]) -> None:
        """Output error message."""
        self.console.print(f"[red]Error:[/red] {data.get('error', 'Unknown error')}")

    def _output_index(self, data: dict[str, Any]) -> None:
        """Output document index."""
        self.console.print(f"\n[bold]{data.get('file', 'Document')}[/bold]")
        self.console.print(f"[dim]Pages: {data.get('pages', '?')} | Type: {data.get('type', 'paper')}[/dim]\n")

        # Metadata
        meta = data.get("metadata", {})
        if meta.get("title"):
            self.console.print(f"[bold]Title:[/bold] {meta['title']}")
        if meta.get("authors"):
            authors = ", ".join(meta["authors"]) if isinstance(meta["authors"], list) else meta["authors"]
            self.console.print(f"[bold]Authors:[/bold] {authors}")

        # Abstract
        if data.get("abstract"):
            self.console.print(f"\n[bold]Abstract:[/bold]")
            self.console.print(f"[dim]{data['abstract'][:300]}{'...' if len(data.get('abstract', '')) > 300 else ''}[/dim]")

        # Sections
        sections = data.get("sections", [])
        if sections:
            self.console.print(f"\n[bold]Sections ({len(sections)}):[/bold]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="cyan", width=4)
            table.add_column("Title")
            table.add_column("Pages", justify="right", width=10)
            for s in sections:
                pages = s.get("pages", [])
                page_str = f"{pages[0]}-{pages[1]}" if len(pages) == 2 else str(pages)
                table.add_row(str(s.get("id", "")), s.get("title", ""), page_str)
            self.console.print(table)

        # Tables summary
        tables = data.get("tables", [])
        if tables:
            self.console.print(f"\n[bold]Tables:[/bold] {len(tables)} found")
            for t in tables[:5]:  # Show first 5
                self.console.print(f"  [cyan]#{t.get('id')}[/cyan] p.{t.get('page')} - {t.get('caption', 'No caption')[:50]}")
            if len(tables) > 5:
                self.console.print(f"  [dim]... and {len(tables) - 5} more[/dim]")

        # Figures summary
        figures = data.get("figures", [])
        if figures:
            self.console.print(f"\n[bold]Figures:[/bold] {len(figures)} found")

        # References
        refs_count = data.get("refs_count", 0)
        if refs_count:
            self.console.print(f"\n[bold]References:[/bold] {refs_count}")

    def _output_chapters(self, data: dict[str, Any]) -> None:
        """Output chapters list."""
        self.console.print(f"\n[bold]{data.get('file', 'Book')}[/bold]")
        self.console.print(f"[dim]Pages: {data.get('pages', '?')}[/dim]\n")

        chapters = data.get("chapters", [])
        self.console.print(f"[bold]Chapters ({len(chapters)}):[/bold]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="cyan", width=4)
        table.add_column("Title")
        table.add_column("Pages", justify="right", width=12)

        for ch in chapters:
            pages = ch.get("pages", [])
            page_str = f"{pages[0]}-{pages[1]}" if len(pages) == 2 else str(pages)
            table.add_row(str(ch.get("id", "")), ch.get("title", ""), page_str)

        self.console.print(table)

    def _output_tables(self, data: dict[str, Any]) -> None:
        """Output tables list."""
        self.console.print(f"\n[bold]Tables from {data.get('file', 'document')}[/bold]")

        tables = data.get("tables", [])
        self.console.print(f"[dim]Found {len(tables)} table(s)[/dim]\n")

        for t in tables:
            self.console.print(f"[bold cyan]Table #{t.get('id')}[/bold cyan] (page {t.get('page')})")
            if t.get("headers"):
                self.console.print(f"[dim]Headers: {' | '.join(str(h) for h in t['headers'][:5])}[/dim]")
            self.console.print(f"[dim]Rows: {t.get('row_count', 0)}, Columns: {t.get('col_count', 0)}[/dim]\n")

    def _output_single_table(self, data: dict[str, Any]) -> None:
        """Output a single table."""
        t = data.get("table", {})
        self.console.print(f"\n[bold cyan]Table #{t.get('id')}[/bold cyan] from {data.get('file', 'document')}")
        self.console.print(f"[dim]Page {t.get('page')}[/dim]\n")

        # Create Rich table
        table = Table(show_header=True, header_style="bold")
        headers = t.get("headers", [])
        for h in headers:
            table.add_column(str(h) if h else "")

        rows = t.get("rows", [])
        for row in rows[:20]:  # Limit rows shown
            table.add_row(*[str(cell) if cell else "" for cell in row])

        self.console.print(table)

        if len(rows) > 20:
            self.console.print(f"[dim]... and {len(rows) - 20} more rows[/dim]")

    def _output_figures(self, data: dict[str, Any]) -> None:
        """Output figures list."""
        self.console.print(f"\n[bold]Figures from {data.get('file', 'document')}[/bold]")

        figures = data.get("figures", [])
        self.console.print(f"[dim]Found {len(figures)} figure(s)[/dim]\n")

        for f in figures:
            self.console.print(f"[bold cyan]Figure #{f.get('id')}[/bold cyan] (page {f.get('page')})")
            self.console.print(f"[dim]Size: {f.get('width')}x{f.get('height')} {f.get('format', 'png')}[/dim]")
            if f.get("caption"):
                self.console.print(f"[dim]Caption: {f['caption'][:60]}[/dim]")
            self.console.print()

    def _output_references(self, data: dict[str, Any]) -> None:
        """Output references list."""
        self.console.print(f"\n[bold]References from {data.get('file', 'document')}[/bold]")

        refs = data.get("references", [])
        self.console.print(f"[dim]Found {len(refs)} reference(s)[/dim]\n")

        for i, ref in enumerate(refs[:20], 1):
            self.console.print(f"[cyan][{i}][/cyan] {ref.get('raw', '')[:100]}")

        if len(refs) > 20:
            self.console.print(f"\n[dim]... and {len(refs) - 20} more[/dim]")

    def _output_text(self, data: dict[str, Any]) -> None:
        """Output extracted text."""
        content = data.get("content", {})
        query = data.get("query", {})

        self.console.print(f"\n[bold]{data.get('file', 'Document')}[/bold]")

        # Show query info
        if query.get("pages"):
            self.console.print(f"[dim]Pages: {query['pages']}[/dim]")
        elif query.get("section"):
            self.console.print(f"[dim]Section: {query['section']}[/dim]")
        elif query.get("chapter"):
            self.console.print(f"[dim]Chapter: {query['chapter']}[/dim]")
        elif query.get("all"):
            self.console.print(f"[dim]Full document[/dim]")

        self.console.print(f"[dim]Words: {content.get('word_count', 0)} | Chars: {content.get('char_count', 0)}[/dim]\n")

        # Output text (truncated for display)
        text = content.get("text", "")
        if len(text) > 2000:
            self.console.print(text[:2000])
            self.console.print(f"\n[dim]... truncated ({len(text) - 2000} more characters)[/dim]")
        else:
            self.console.print(text)


def get_formatter(
    json_flag: bool = False,
    pretty_flag: bool = False,
) -> OutputFormatter:
    """Get an output formatter with the specified flags.

    Args:
        json_flag: Force JSON output.
        pretty_flag: Force pretty output.

    Returns:
        Configured OutputFormatter instance.
    """
    return OutputFormatter(
        force_json=json_flag,
        force_pretty=pretty_flag,
    )
