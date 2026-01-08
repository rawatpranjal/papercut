"""Output formatter with JSON/pretty modes and TTY detection."""

import io
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.table import Table

# Type alias for pretty formatter functions
PrettyFn = Callable[["dict[str, Any]", Console], None]


@dataclass
class OutputFormatter:
    """Handles output formatting with JSON/pretty modes.

    Auto-detects TTY for default mode:
    - TTY (terminal): Pretty formatted output with colors
    - Non-TTY (pipe/redirect): JSON output for machine consumption

    Supports quiet mode to suppress all output.
    """

    force_json: bool = False
    force_pretty: bool = False
    quiet: bool = False
    _console: Console | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._console is None:
            if self.quiet:
                # Null console - discards output
                self._console = Console(file=io.StringIO())
            else:
                self._console = Console()

    @property
    def console(self) -> Console:
        """Get the console instance (guaranteed non-None after init)."""
        assert self._console is not None
        return self._console

    @property
    def use_json(self) -> bool:
        """Determine if JSON output should be used."""
        if self.force_json:
            return True
        if self.force_pretty:
            return False
        # Auto-detect: JSON if stdout is not a TTY
        return not sys.stdout.isatty()

    def output(self, data: dict[str, Any], pretty_fn: PrettyFn | None = None) -> None:
        """Output data in appropriate format.

        Args:
            data: Dictionary to output.
            pretty_fn: Optional function to render pretty output.
                       If not provided, uses default pretty formatter.
        """
        if self.quiet:
            return  # Suppress all output in quiet mode

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
        elif "reading_time" in data:
            # Paper/document info with statistics
            self._output_info(data)
        elif "section" in data and "content" in data:
            # Section content extraction (specific section)
            self._output_section_content(data)
        elif "sections" in data and "count" in data and "type" not in data:
            # Section list only (from extract section --list)
            self._output_section_list(data)
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
        elif "equations" in data:
            self._output_equations(data)
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

    def _output_info(self, data: dict[str, Any]) -> None:
        """Output paper/document info with statistics."""
        self.console.print(f"\n[bold]{data.get('file', 'Document')}[/bold]\n")

        # Metadata
        meta = data.get("metadata", {})
        if meta.get("title"):
            self.console.print(f"[bold]Title:[/bold] {meta['title']}")
        if meta.get("authors"):
            authors = ", ".join(meta["authors"]) if isinstance(meta["authors"], list) else meta["authors"]
            self.console.print(f"[bold]Authors:[/bold] {authors}")

        # Basic stats
        self.console.print()
        self.console.print(f"[dim]Pages:[/dim]      {data.get('pages', 0):,}")
        self.console.print(f"[dim]Words:[/dim]      {data.get('words', 0):,}")
        self.console.print(f"[dim]Figures:[/dim]    {data.get('figures', 0)}")
        self.console.print(f"[dim]Tables:[/dim]     {data.get('tables', 0)}")
        self.console.print(f"[dim]References:[/dim] {data.get('references', 0)}")

        # Reading time
        rt = data.get("reading_time", {})
        if rt:
            minutes = rt.get("minutes", 0)
            wpm = rt.get("wpm", 250)
            if minutes >= 60:
                hours = minutes // 60
                mins = minutes % 60
                time_str = f"{hours}h {mins}min" if mins > 0 else f"{hours}h"
            else:
                time_str = f"{minutes} min"
            self.console.print(f"\n[bold]Est. reading time:[/bold] {time_str} (at {wpm} wpm)")

        # Sections table (for papers with word counts)
        sections = data.get("sections", [])
        if sections and any("word_count" in s for s in sections):
            self.console.print("\n[bold]Sections:[/bold]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="cyan", width=4)
            table.add_column("Title")
            table.add_column("Pages", justify="right", width=10)
            table.add_column("Words", justify="right", width=8)
            for s in sections:
                pages = s.get("pages", [])
                if len(pages) == 2 and pages[0] != pages[1]:
                    page_str = f"{pages[0]}-{pages[1]}"
                else:
                    page_str = str(pages[0] if pages else "")
                table.add_row(
                    str(s.get("id", "")),
                    s.get("title", ""),
                    page_str,
                    f"{s.get('word_count', 0):,}",
                )
            self.console.print(table)

        # Chapters (for books)
        chapters = data.get("chapters", [])
        if chapters:
            self.console.print(f"\n[bold]Chapters ({len(chapters)}):[/bold]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="cyan", width=4)
            table.add_column("Title")
            table.add_column("Pages", justify="right", width=12)
            for ch in chapters:
                pages = ch.get("pages", [])
                page_str = f"{pages[0]}-{pages[1]}" if len(pages) == 2 else str(pages)
                table.add_row(str(ch.get("id", "")), ch.get("title", ""), page_str)
            self.console.print(table)

    def _output_section_list(self, data: dict[str, Any]) -> None:
        """Output section list (from extract section --list)."""
        self.console.print(f"\n[bold]{data.get('file', 'Document')}[/bold]\n")

        sections = data.get("sections", [])
        self.console.print(f"[bold]Sections ({len(sections)}):[/bold]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("ID", style="cyan", width=4)
        table.add_column("Title")
        table.add_column("Pages", justify="right", width=10)

        for s in sections:
            pages = s.get("pages", [])
            if len(pages) == 2 and pages[0] != pages[1]:
                page_str = f"{pages[0]}-{pages[1]}"
            else:
                page_str = str(pages[0] if pages else "")
            table.add_row(str(s.get("id", "")), s.get("title", ""), page_str)

        self.console.print(table)

    def _output_section_content(self, data: dict[str, Any]) -> None:
        """Output extracted section content."""
        sec = data.get("section", {})
        content = data.get("content", {})

        self.console.print(f"\n[bold]{data.get('file', 'Document')}[/bold]")

        pages = sec.get("pages", [])
        if len(pages) == 2 and pages[0] != pages[1]:
            page_str = f"{pages[0]}-{pages[1]}"
        else:
            page_str = str(pages[0] if pages else "")
        self.console.print(f"[dim]Section: {sec.get('title', '')} (pages {page_str})[/dim]")
        self.console.print(
            f"[dim]Words: {content.get('word_count', 0):,} | "
            f"Chars: {content.get('char_count', 0):,}[/dim]\n"
        )

        text = content.get("text", "")
        # Truncate for terminal display
        if len(text) > 3000:
            self.console.print(text[:3000])
            self.console.print(f"\n[dim]... truncated ({len(text) - 3000:,} more characters)[/dim]")
        else:
            self.console.print(text)

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
            self.console.print("\n[bold]Abstract:[/bold]")
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

    def _output_equations(self, data: dict[str, Any]) -> None:
        """Output equations list."""
        self.console.print(f"\n[bold]Equations from {data.get('file', 'document')}[/bold]")

        equations = data.get("equations", [])
        method = data.get("method")
        low_conf = data.get("low_confidence_count", 0)

        self.console.print(f"[dim]Found {len(equations)} equation(s)")
        if method:
            self.console.print(f"LaTeX method: {method}[/dim]")
        else:
            self.console.print("[/dim]")
        if low_conf > 0:
            self.console.print(f"[yellow]Low confidence: {low_conf}[/yellow]")
        self.console.print()

        for eq in equations[:20]:
            type_str = eq.get("type", "display")
            type_badge = "[cyan]display[/cyan]" if type_str == "display" else "[dim]inline[/dim]"

            self.console.print(
                f"[bold]Equation #{eq.get('id')}[/bold] (page {eq.get('page')}) {type_badge}"
            )

            if eq.get("image_path"):
                self.console.print(f"  [dim]Image: {eq['image_path']}[/dim]")

            if eq.get("latex"):
                latex_info = eq["latex"]
                latex_text = latex_info.get("latex", "")
                conf = latex_info.get("confidence", 0)
                conf_style = "green" if conf >= 0.9 else ("yellow" if conf >= 0.7 else "red")

                # Truncate long LaTeX
                display_latex = latex_text[:60] + "..." if len(latex_text) > 60 else latex_text
                self.console.print(f"  [dim]LaTeX:[/dim] {display_latex}")
                self.console.print(f"  [{conf_style}]Confidence: {conf:.1%}[/{conf_style}]")

            if eq.get("context"):
                context = eq["context"]
                display_context = context[:50] + "..." if len(context) > 50 else context
                self.console.print(f"  [dim]Context: {display_context}[/dim]")

            self.console.print()

        if len(equations) > 20:
            self.console.print(f"[dim]... and {len(equations) - 20} more equations[/dim]")

    def _output_references(self, data: dict[str, Any]) -> None:
        """Output references list."""
        self.console.print(f"\n[bold]References from {data.get('file', 'document')}[/bold]")

        refs = data.get("references", [])
        self.console.print(f"[dim]Found {len(refs)} reference(s)[/dim]\n")

        for i, ref in enumerate(refs[:20], 1):
            self.console.print(f"[cyan][{i}][/cyan] {ref.get('raw_text', '')[:100]}")

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
            self.console.print("[dim]Full document[/dim]")

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
    quiet: bool = False,
) -> OutputFormatter:
    """Get an output formatter with the specified flags.

    Args:
        json_flag: Force JSON output.
        pretty_flag: Force pretty output.
        quiet: Suppress all output.

    Returns:
        Configured OutputFormatter instance.
    """
    return OutputFormatter(
        force_json=json_flag,
        force_pretty=pretty_flag,
        quiet=quiet,
    )
