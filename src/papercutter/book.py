"""Book processing: chapter detection, summarization, and synthesis."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pypdf import PdfReader
from rich.console import Console
from rich.progress import track

logger = logging.getLogger(__name__)
console = Console()


# --- Data Models ---


class Chapter(BaseModel):
    """A detected chapter in a book."""

    number: int
    title: str
    start_page: int  # 1-indexed
    end_page: int  # 1-indexed, inclusive
    confidence: float = 1.0

    @property
    def page_count(self) -> int:
        """Number of pages in this chapter."""
        return self.end_page - self.start_page + 1


class ChapterSummary(BaseModel):
    """Extracted summary for a chapter."""

    chapter_num: int
    main_thesis: str  # What is this chapter arguing?
    unique_insight: str  # What's novel that ONLY this chapter provides?
    key_evidence: str  # Examples, data, arguments
    counterexample: str = ""  # What this approach is NOT
    how_to: str = ""  # Operational details, practical steps
    practical_implications: str = ""  # What should the reader DO?
    builds_on: str  # "Extends Ch 2's framework..."
    enables: str  # "Sets up Ch 7..."
    golden_quote: str | None = None
    key_terms: list[str] = []


class BookSynthesis(BaseModel):
    """Book-level synthesis from all chapter summaries."""

    book_thesis: str
    key_themes: list[str]
    intellectual_journey: str
    one_paragraph_summary: str


class BookInventory(BaseModel):
    """State for a book processing session."""

    title: str
    pdf_path: str
    status: str = "indexed"  # indexed | extracted | summarized | reported
    chapters: list[Chapter] = []
    summaries: list[ChapterSummary] = []
    synthesis: BookSynthesis | None = None

    @classmethod
    def load(cls, project_dir: Path) -> "BookInventory":
        """Load book inventory from project directory."""
        path = project_dir / "book_inventory.json"
        if path.exists():
            return cls.model_validate_json(path.read_text())
        raise FileNotFoundError(
            "No book_inventory.json found. Run 'papercutter book index' first."
        )

    def save(self, project_dir: Path) -> None:
        """Save book inventory to project directory."""
        path = project_dir / "book_inventory.json"
        path.write_text(self.model_dump_json(indent=2))


# --- Chapter Detection ---


# Regex patterns for chapter headings
CHAPTER_PATTERNS = [
    # "1\nIntroduction and Motivation" - number on its own line
    re.compile(r"^(\d+)\s*\n\s*([A-Z][A-Za-z\s,':]+)", re.MULTILINE),
    # "Chapter 1: Introduction" or "CHAPTER 1. Title"
    re.compile(r"^(?:Chapter|CHAPTER)\s+(\d+)[:\.\s]+(.+)", re.MULTILINE),
]

# Patterns to exclude (Part headers, section dividers, etc.)
EXCLUDE_PATTERNS = [
    re.compile(r"topics?\s+for", re.IGNORECASE),
    re.compile(r"^part\s+", re.IGNORECASE),
    re.compile(r"selected\s+topics?", re.IGNORECASE),
    re.compile(r"advanced\s+topics?", re.IGNORECASE),
    re.compile(r"complementary\s+and\s+alternative", re.IGNORECASE),
]


def detect_chapters_from_outline(reader: PdfReader) -> list[Chapter]:
    """Extract chapters from PDF outline/bookmarks if available."""
    if not reader.outline:
        return []

    chapters = []
    chapter_num = 0

    def process_outline(outline: list, level: int = 0) -> None:
        nonlocal chapter_num
        for item in outline:
            if isinstance(item, list):
                process_outline(item, level + 1)
            else:
                try:
                    title = item.title if hasattr(item, "title") else str(item)
                    page_num = None
                    if hasattr(item, "page") and item.page:
                        page_num = reader.get_page_number(item.page) + 1

                    # Only count top-level items as chapters
                    if level == 0 and page_num:
                        chapter_num += 1
                        chapters.append(
                            Chapter(
                                number=chapter_num,
                                title=title.strip(),
                                start_page=page_num,
                                end_page=page_num,  # Will be updated
                            )
                        )
                except Exception:
                    continue

    process_outline(reader.outline)

    # Set end pages based on next chapter start
    for i, chapter in enumerate(chapters):
        if i + 1 < len(chapters):
            chapter.end_page = chapters[i + 1].start_page - 1
        else:
            chapter.end_page = len(reader.pages)

    return chapters


def _is_excluded_title(title: str) -> bool:
    """Check if a title matches exclusion patterns (Part headers, etc.)."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern.search(title):
            return True
    return False


def detect_chapters_from_text(reader: PdfReader) -> list[Chapter]:
    """Detect chapters by scanning page text for chapter headings."""
    raw_chapters = []

    for page_num in range(len(reader.pages)):
        text = reader.pages[page_num].extract_text() or ""
        first_300 = text[:300].strip()

        for pattern in CHAPTER_PATTERNS:
            match = pattern.match(first_300)
            if match:
                num_str, title = match.groups()
                title = title.strip().split("\n")[0][:80]  # Truncate long titles

                # Skip Part headers and other excluded patterns
                if _is_excluded_title(title):
                    break

                # Convert roman numerals or strings to int
                try:
                    num = int(num_str)
                except ValueError:
                    num = len(raw_chapters) + 1

                raw_chapters.append(
                    Chapter(
                        number=num,
                        title=title,
                        start_page=page_num + 1,
                        end_page=page_num + 1,  # Will be updated
                    )
                )
                break  # Found a match, move to next page

    # Renumber chapters sequentially (in case of gaps/duplicates)
    chapters = []
    for i, ch in enumerate(raw_chapters, 1):
        chapters.append(
            Chapter(
                number=i,
                title=ch.title,
                start_page=ch.start_page,
                end_page=ch.end_page,
            )
        )

    # Set end pages based on next chapter start
    total_pages = len(reader.pages)
    for i, chapter in enumerate(chapters):
        if i + 1 < len(chapters):
            chapter.end_page = chapters[i + 1].start_page - 1
        else:
            chapter.end_page = total_pages

    return chapters


def detect_chapters(pdf_path: Path) -> list[Chapter]:
    """Detect chapters in a PDF using outline or text patterns.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of detected chapters.
    """
    reader = PdfReader(pdf_path)

    # Try outline first
    chapters = detect_chapters_from_outline(reader)
    if chapters:
        logger.info(f"Found {len(chapters)} chapters from PDF outline")
        return chapters

    # Fall back to text pattern matching
    chapters = detect_chapters_from_text(reader)
    if chapters:
        logger.info(f"Found {len(chapters)} chapters from text patterns")
        return chapters

    # Last resort: treat entire book as one chapter
    logger.warning("No chapters detected, treating book as single chapter")
    return [
        Chapter(
            number=1,
            title="Full Book",
            start_page=1,
            end_page=len(reader.pages),
        )
    ]


# --- Chapter Text Extraction ---


def extract_chapter_text(
    pdf_path: Path,
    chapter: Chapter,
) -> str:
    """Extract text for a specific chapter using pypdf.

    Args:
        pdf_path: Path to the PDF file.
        chapter: Chapter to extract.

    Returns:
        Extracted chapter text.
    """
    reader = PdfReader(pdf_path)
    text_parts = []

    for page_num in range(chapter.start_page - 1, chapter.end_page):
        page_text = reader.pages[page_num].extract_text() or ""
        text_parts.append(page_text)

    return "\n\n".join(text_parts)


# --- LLM Summarization ---


CHAPTER_SUMMARY_PROMPT = """Summarize this book chapter in depth. Be SPECIFIC and SUBSTANTIVE.

BOOK: {book_title}
CHAPTER {chapter_num}/{total_chapters}: "{chapter_title}" (pp. {start_page}-{end_page})

{previous_context}

CHAPTER TEXT:
{chapter_text}

---
EXTRACT THE FOLLOWING (give each field real substance):

1. MAIN THESIS (2-3 sentences)
The core argument stated DIRECTLY. SHOW the insight, don't summarize it.
BAD: "This chapter provides a comprehensive framework for..."
GOOD: "Online controlled experiments are the gold standard for..."
Start with the claim itself, not meta-commentary about the chapter.

2. UNIQUE INSIGHT (3-4 sentences)
What NEW framework, technique, or idea does THIS chapter introduce?
Explain it in enough detail that someone could understand the concept without reading the chapter.

3. KEY EVIDENCE (3-4 sentences with multiple examples)
Concrete examples, case studies, data points that support the thesis.
Include company names, specific numbers, years, and citations where available.

4. COUNTEREXAMPLE (1-2 sentences)
What is this chapter's approach NOT? What common mistake or alternative does it warn against?
Use a specific example from the text if available.
Example: "This is NOT correlation-based inference—the chapter warns against assuming causality from observational data."

5. HOW TO (2-3 sentences)
The operational details or practical steps to implement the chapter's approach.
What are the concrete mechanics? How does one actually do this?
Example: "Run experiments with minimum 2-week duration. Use Sample Ratio Mismatch checks with p<0.001 threshold. Define OEC before experiment starts."

6. PRACTICAL IMPLICATIONS (2-3 sentences)
What should a practitioner DO differently after reading this chapter?
What's the actionable takeaway?

7. BUILDS ON (chapter numbers only)
Format: "Ch 1, 2" or "Standalone"
Do NOT include descriptions like "Ch 1: Overall Evaluation Criterion"

8. ENABLES (chapter numbers only)
Format: "Ch 7, 8, 12" or "Concluding"
Do NOT include descriptions like "Ch 7: OEC details"

9. GOLDEN QUOTE (exact text from chapter, or null)
One memorable sentence that captures the chapter's essence.

10. KEY TERMS (3-5 terms)
New concepts introduced in THIS chapter.

Return JSON:
{{
  "main_thesis": "...",
  "unique_insight": "...",
  "key_evidence": "...",
  "counterexample": "...",
  "how_to": "...",
  "practical_implications": "...",
  "builds_on": "...",
  "enables": "...",
  "golden_quote": "..." or null,
  "key_terms": ["term1", "term2", ...]
}}
"""


def _format_previous_context(summaries: list[ChapterSummary]) -> str:
    """Format previous chapter summaries as condensed context."""
    if not summaries:
        return "PREVIOUS CHAPTERS: This is the first chapter."

    lines = ["PREVIOUS CHAPTERS (for context):"]
    for s in summaries:
        lines.append(f"  Ch {s.chapter_num}: {s.main_thesis}")
        if s.key_terms:
            lines.append(f"    Key terms: {', '.join(s.key_terms[:5])}")

    return "\n".join(lines)


def summarize_chapter(
    completion_fn: Any,
    chapter_text: str,
    chapter: Chapter,
    book_title: str,
    total_chapters: int,
    previous_summaries: list[ChapterSummary],
) -> ChapterSummary:
    """Summarize a single chapter using LLM.

    Args:
        completion_fn: LiteLLM completion function.
        chapter_text: Full text of the chapter.
        chapter: Chapter metadata.
        book_title: Title of the book.
        total_chapters: Total number of chapters.
        previous_summaries: Summaries of previous chapters for context.

    Returns:
        ChapterSummary with extracted fields.
    """
    import json_repair

    # Truncate very long chapters
    max_chars = 100000  # ~25K tokens
    if len(chapter_text) > max_chars:
        # Keep beginning and end
        first_part = chapter_text[: int(max_chars * 0.7)]
        last_part = chapter_text[-int(max_chars * 0.3) :]
        chapter_text = (
            first_part
            + "\n\n[...MIDDLE SECTION OMITTED DUE TO LENGTH...]\n\n"
            + last_part
        )

    prompt = CHAPTER_SUMMARY_PROMPT.format(
        book_title=book_title,
        chapter_num=chapter.number,
        total_chapters=total_chapters,
        chapter_title=chapter.title,
        start_page=chapter.start_page,
        end_page=chapter.end_page,
        previous_context=_format_previous_context(previous_summaries),
        chapter_text=chapter_text,
    )

    response = completion_fn(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    try:
        data = json_repair.loads(raw)
    except Exception:
        data = json.loads(raw)

    return ChapterSummary(
        chapter_num=chapter.number,
        main_thesis=data.get("main_thesis", ""),
        unique_insight=data.get("unique_insight", ""),
        key_evidence=data.get("key_evidence", ""),
        counterexample=data.get("counterexample", ""),
        how_to=data.get("how_to", ""),
        practical_implications=data.get("practical_implications", ""),
        builds_on=data.get("builds_on", ""),
        enables=data.get("enables", ""),
        golden_quote=data.get("golden_quote"),
        key_terms=data.get("key_terms", []),
    )


# --- Book Synthesis ---


BOOK_SYNTHESIS_PROMPT = """Synthesize these chapter summaries into a book-level overview.

BOOK: {book_title}
CHAPTERS: {num_chapters}

CHAPTER SUMMARIES:
{chapter_summaries}

GENERATE:

1. BOOK THESIS (2-3 sentences)
What is the book's central argument or purpose?
What question does it answer?

2. KEY THEMES (exactly 3 themes, 3-5 words each)
The three core ideas that recur across chapters.
Format: Short, punchy phrases WITHOUT parenthetical explanations.
GOOD: "Systematic skepticism over celebration"
BAD: "Systematic Skepticism and Validation (e.g., Twyman's Law, Sample Ratio Mismatch checks)"

3. INTELLECTUAL JOURNEY (2-3 sentences)
How does the book build its argument chapter by chapter?
What is the logical progression?

4. ONE PARAGRAPH SUMMARY (100-150 words)
A dense, information-rich paragraph summarizing the entire book.
Suitable for someone deciding whether to read it.

Return valid JSON:
{{
  "book_thesis": "...",
  "key_themes": ["theme1", "theme2", ...],
  "intellectual_journey": "...",
  "one_paragraph_summary": "..."
}}
"""


def synthesize_book(
    completion_fn: Any,
    book_title: str,
    summaries: list[ChapterSummary],
) -> BookSynthesis:
    """Generate book-level synthesis from chapter summaries.

    Args:
        completion_fn: LiteLLM completion function.
        book_title: Title of the book.
        summaries: All chapter summaries.

    Returns:
        BookSynthesis with book-level insights.
    """
    import json_repair

    # Format chapter summaries
    formatted = []
    for s in summaries:
        formatted.append(
            f"Chapter {s.chapter_num}: {s.main_thesis}\n"
            f"  Unique insight: {s.unique_insight}\n"
            f"  Key terms: {', '.join(s.key_terms)}"
        )

    prompt = BOOK_SYNTHESIS_PROMPT.format(
        book_title=book_title,
        num_chapters=len(summaries),
        chapter_summaries="\n\n".join(formatted),
    )

    response = completion_fn(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    raw = response.choices[0].message.content
    try:
        data = json_repair.loads(raw)
    except Exception:
        data = json.loads(raw)

    return BookSynthesis(
        book_thesis=data.get("book_thesis", ""),
        key_themes=data.get("key_themes", []),
        intellectual_journey=data.get("intellectual_journey", ""),
        one_paragraph_summary=data.get("one_paragraph_summary", ""),
    )


# --- CLI Entry Points ---


def run_book_index(pdf_path: Path) -> None:
    """Detect chapters and create book inventory.

    Args:
        pdf_path: Path to the book PDF.
    """
    console.print(f"[dim]Indexing:[/dim] {pdf_path.name}")

    chapters = detect_chapters(pdf_path)

    if not chapters:
        console.print("[red]Error:[/red] No chapters detected")
        return

    # Get book title from first page or filename
    reader = PdfReader(pdf_path)
    first_page = reader.pages[0].extract_text() or ""
    title = first_page.split("\n")[0][:100].strip() or pdf_path.stem

    inventory = BookInventory(
        title=title,
        pdf_path=str(pdf_path.absolute()),
        status="indexed",
        chapters=chapters,
    )

    project_dir = Path.cwd()
    inventory.save(project_dir)

    console.print(f"\n[green]Found {len(chapters)} chapters:[/green]")
    for ch in chapters:
        console.print(
            f"  [cyan]{ch.number:2}.[/cyan] {ch.title} "
            f"[dim](pp. {ch.start_page}-{ch.end_page})[/dim]"
        )

    console.print(f"\n[dim]Saved to:[/dim] book_inventory.json")


def run_book_extract(use_docling: bool = False) -> None:
    """Extract chapter text from PDF.

    Args:
        use_docling: Use Docling for rich markdown extraction.
    """
    project_dir = Path.cwd()
    inventory = BookInventory.load(project_dir)

    pdf_path = Path(inventory.pdf_path)
    if not pdf_path.exists():
        console.print(f"[red]Error:[/red] PDF not found: {pdf_path}")
        return

    chapters_dir = project_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)

    console.print(f"[dim]Extracting {len(inventory.chapters)} chapters...[/dim]")

    for chapter in track(inventory.chapters, description="Extracting..."):
        if use_docling:
            # TODO: Implement Docling per-chapter extraction
            console.print("[yellow]Warning:[/yellow] Docling extraction not yet implemented")
            text = extract_chapter_text(pdf_path, chapter)
            ext = ".md"
        else:
            text = extract_chapter_text(pdf_path, chapter)
            ext = ".txt"

        # Save chapter text
        filename = f"{chapter.number:02d}_{chapter.title.lower().replace(' ', '_')[:40]}{ext}"
        filepath = chapters_dir / filename
        filepath.write_text(text, encoding="utf-8")

    inventory.status = "extracted"
    inventory.save(project_dir)

    console.print(f"\n[green]Extracted {len(inventory.chapters)} chapters[/green]")
    console.print(f"[dim]Saved to:[/dim] {chapters_dir}")


def run_book_summarize() -> None:
    """Summarize each chapter with LLM."""
    try:
        from litellm import completion
    except ImportError:
        console.print(
            "[red]Error:[/red] litellm not installed. "
            "Install with: pip install 'papercutter[full]'"
        )
        return

    project_dir = Path.cwd()
    inventory = BookInventory.load(project_dir)

    pdf_path = Path(inventory.pdf_path)
    chapters_dir = project_dir / "chapters"

    console.print(f"[dim]Summarizing {len(inventory.chapters)} chapters...[/dim]")

    summaries: list[ChapterSummary] = []

    for chapter in track(inventory.chapters, description="Summarizing..."):
        # Find chapter file
        pattern = f"{chapter.number:02d}_*"
        files = list(chapters_dir.glob(pattern))
        if files:
            chapter_text = files[0].read_text(encoding="utf-8")
        else:
            # Fall back to extracting from PDF
            chapter_text = extract_chapter_text(pdf_path, chapter)

        summary = summarize_chapter(
            completion_fn=completion,
            chapter_text=chapter_text,
            chapter=chapter,
            book_title=inventory.title,
            total_chapters=len(inventory.chapters),
            previous_summaries=summaries,
        )
        summaries.append(summary)

        console.print(
            f"  [green]Ch {chapter.number}:[/green] {summary.main_thesis[:60]}..."
        )

    # Synthesize book
    console.print("\n[dim]Synthesizing book overview...[/dim]")
    synthesis = synthesize_book(
        completion_fn=completion,
        book_title=inventory.title,
        summaries=summaries,
    )

    inventory.summaries = summaries
    inventory.synthesis = synthesis
    inventory.status = "summarized"
    inventory.save(project_dir)

    # Also save extractions as separate file
    extractions = {
        "book_title": inventory.title,
        "synthesis": synthesis.model_dump(),
        "chapters": [s.model_dump() for s in summaries],
    }
    extractions_path = project_dir / "book_extractions.json"
    extractions_path.write_text(json.dumps(extractions, indent=2, ensure_ascii=False))

    console.print(f"\n[green]Summarized {len(summaries)} chapters[/green]")
    console.print(f"[dim]Book thesis:[/dim] {synthesis.book_thesis[:100]}...")
    console.print(f"[dim]Saved to:[/dim] book_extractions.json")


def run_book_report() -> None:
    """Generate book summary PDF report."""
    try:
        import jinja2
    except ImportError:
        console.print(
            "[red]Error:[/red] jinja2 not installed. "
            "Install with: pip install 'papercutter[full]'"
        )
        return

    project_dir = Path.cwd()
    inventory = BookInventory.load(project_dir)

    if not inventory.synthesis:
        console.print(
            "[red]Error:[/red] No synthesis found. Run 'papercutter book summarize' first."
        )
        return

    # Load template
    template_dir = Path(__file__).parent / "templates"
    template_path = template_dir / "book_report.tex.j2"

    if not template_path.exists():
        console.print(f"[red]Error:[/red] Template not found: {template_path}")
        return

    # Create output directory
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Load and render template
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
    )

    # Add filters
    from papercutter.report import latex_escape, markdown_to_latex

    env.filters["latex_escape"] = latex_escape
    env.filters["markdown_to_latex"] = markdown_to_latex

    template = env.get_template("book_report.tex.j2")

    # Build chapter data
    chapters_data = []
    for ch, summary in zip(inventory.chapters, inventory.summaries):
        chapters_data.append(
            {
                "number": ch.number,
                "title": ch.title,
                "start_page": ch.start_page,
                "end_page": ch.end_page,
                "main_thesis": summary.main_thesis,
                "unique_insight": summary.unique_insight,
                "key_evidence": summary.key_evidence,
                "counterexample": summary.counterexample,
                "how_to": summary.how_to,
                "practical_implications": summary.practical_implications,
                "builds_on": summary.builds_on,
                "enables": summary.enables,
                "golden_quote": summary.golden_quote,
                "key_terms": summary.key_terms,
            }
        )

    # Render
    rendered = template.render(
        book_title=inventory.title,
        synthesis=inventory.synthesis.model_dump(),
        chapters=chapters_data,
        chapter_count=len(chapters_data),
    )

    # Save LaTeX source
    tex_path = output_dir / "book_summary.tex"
    tex_path.write_text(rendered, encoding="utf-8")

    # Compile PDF
    import subprocess

    console.print("[dim]Compiling PDF...[/dim]")
    try:
        for _ in range(2):  # Run twice for references
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path.name],
                cwd=output_dir,
                capture_output=True,
                check=True,
            )

        # Clean up auxiliary files
        for ext in [".aux", ".log", ".out", ".toc"]:
            aux_file = output_dir / f"book_summary{ext}"
            if aux_file.exists():
                aux_file.unlink()

        console.print(f"\n[green]Generated report:[/green] {output_dir / 'book_summary.pdf'}")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error compiling PDF:[/red] {e}")
        console.print(f"[dim]LaTeX source saved to:[/dim] {tex_path}")
    except FileNotFoundError:
        console.print(
            "[yellow]Warning:[/yellow] pdflatex not found. "
            f"LaTeX source saved to: {tex_path}"
        )
