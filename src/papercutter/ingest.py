"""Docling wrapper - PDF to Markdown + Tables extraction."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import track

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class ExtractedTable:
    """A table extracted from a PDF."""

    page: int
    data: list[dict[str, Any]]
    caption: str | None = None


@dataclass
class ExtractedFigure:
    """A figure extracted from a PDF."""

    page: int
    image_path: str
    caption: str | None = None


@dataclass
class IngestResult:
    """Result of PDF ingestion."""

    markdown: str
    tables: list[ExtractedTable] = field(default_factory=list)
    figures: list[ExtractedFigure] = field(default_factory=list)
    title: str | None = None
    page_count: int = 0


def _check_docling() -> bool:
    """Check if Docling is available."""
    try:
        import docling  # noqa: F401

        return True
    except ImportError:
        return False


def is_garbage_content(text: str) -> bool:
    """Detect PDF encoding failures like /G31 hex codes.

    Some PDFs use Type 3 fonts or glyph subsets that extractors can't decode,
    resulting in garbage like '/G31/G25/G28' instead of readable text.

    Args:
        text: The extracted text content.

    Returns:
        True if content appears to be garbage/unreadable.
    """
    if len(text) < 100:
        return True

    # Count garbage patterns in first 1000 chars
    sample = text[:1000]
    garbage_patterns = ["/G", "\\x", "\x00", "\ufffd"]
    garbage_count = sum(sample.count(p) for p in garbage_patterns)

    # If >10% is garbage patterns, flag it
    return garbage_count > len(sample) * 0.1


def pypdf_extract(pdf_path: Path) -> str:
    """Simple text extraction via pypdf as fallback.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text content.
    """
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n\n"
    return text


def convert_pdf(pdf_path: Path, figures_dir: Path | None = None) -> IngestResult:
    """Convert a PDF to Markdown + Tables + Figures using Docling.

    Args:
        pdf_path: Path to the PDF file.
        figures_dir: Directory to save extracted figures. If None, figures not saved.

    Returns:
        IngestResult with markdown content, extracted tables, and figures.

    Raises:
        ImportError: If Docling is not installed.
        RuntimeError: If conversion fails.
    """
    if not _check_docling():
        raise ImportError(
            "Docling is not installed. Install with: pip install 'papercutter[docling]'"
        )

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    # Configure pipeline
    options = PdfPipelineOptions()
    options.do_ocr = True
    options.do_table_structure = True
    options.generate_picture_images = True  # Enable figure extraction

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )

    try:
        result = converter.convert(str(pdf_path))
        doc = result.document

        # Export to markdown
        markdown = doc.export_to_markdown()

        # Extract tables
        tables: list[ExtractedTable] = []
        try:
            from docling_core.types.doc import TableItem

            for element, _ in doc.iterate_items():
                if isinstance(element, TableItem):
                    try:
                        # Pass doc argument to avoid deprecation warning
                        df = element.export_to_dataframe(doc)
                        table_data = df.to_dict("records")
                        tables.append(
                            ExtractedTable(
                                page=getattr(element, "page_no", 0),
                                data=table_data,
                                caption=getattr(element, "caption", None),
                            )
                        )
                    except Exception as e:
                        logger.debug(f"Failed to extract table: {e}")
        except ImportError:
            logger.debug("docling_core not available for table extraction")

        # Extract figures
        figures: list[ExtractedFigure] = []
        try:
            from docling_core.types.doc import PictureItem

            fig_count = 0
            for element, _ in doc.iterate_items():
                if isinstance(element, PictureItem):
                    try:
                        fig_count += 1
                        # Save figure image if directory provided
                        image_path = ""
                        if figures_dir and hasattr(element, "image") and element.image:
                            figures_dir.mkdir(parents=True, exist_ok=True)
                            img_filename = f"figure_{fig_count}.png"
                            img_path = figures_dir / img_filename
                            # Save PIL image
                            if hasattr(element.image, "pil_image"):
                                element.image.pil_image.save(str(img_path))
                                image_path = str(img_path)
                            elif hasattr(element, "get_image"):
                                img = element.get_image(doc)
                                if img:
                                    img.save(str(img_path))
                                    image_path = str(img_path)

                        figures.append(
                            ExtractedFigure(
                                page=getattr(element, "page_no", 0),
                                image_path=image_path,
                                caption=getattr(element, "caption", None),
                            )
                        )
                    except Exception as e:
                        logger.debug(f"Failed to extract figure: {e}")
        except ImportError:
            logger.debug("docling_core not available for figure extraction")

        # Get title from document name or first line
        title = getattr(doc, "name", None)
        if not title and markdown:
            first_line = markdown.split("\n")[0].strip()
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()

        # Get page count
        page_count = getattr(doc, "num_pages", 0) if hasattr(doc, "num_pages") else 0

        return IngestResult(
            markdown=markdown,
            tables=tables,
            figures=figures,
            title=title,
            page_count=page_count,
        )

    except Exception as e:
        raise RuntimeError(f"Failed to convert {pdf_path.name}: {e}") from e


def run_ingest(source: Path) -> None:
    """Process all PDFs in a source directory.

    Args:
        source: Directory containing PDF files.
    """
    from papercutter.project import Inventory

    project_dir = Path.cwd()
    inventory = Inventory.load(project_dir)

    # Find all PDFs
    pdfs = list(source.glob("*.pdf"))
    if not pdfs:
        console.print(f"[yellow]Warning:[/yellow] No PDF files found in {source}")
        return

    console.print(f"Found [bold]{len(pdfs)}[/bold] PDF files")

    # Create output directories
    md_dir = project_dir / "markdown"
    md_dir.mkdir(exist_ok=True)
    tables_dir = project_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    figures_base_dir = project_dir / "figures"
    figures_base_dir.mkdir(exist_ok=True)

    success_count = 0
    error_count = 0

    for pdf in track(pdfs, description="Ingesting PDFs..."):
        try:
            # Create per-paper figures directory
            paper_figures_dir = figures_base_dir / pdf.stem
            result = convert_pdf(pdf, figures_dir=paper_figures_dir)

            # Check for garbage content and try pypdf fallback
            if is_garbage_content(result.markdown):
                console.print(
                    f"[yellow]Warning:[/yellow] {pdf.name} has unreadable content (font encoding issue)"
                )
                console.print("[dim]Trying pypdf fallback...[/dim]")
                fallback_text = pypdf_extract(pdf)
                if not is_garbage_content(fallback_text):
                    console.print("[green]pypdf fallback succeeded[/green]")
                    result = IngestResult(
                        markdown=fallback_text,
                        tables=[],  # pypdf doesn't extract tables
                        figures=[],
                        title=result.title,
                        page_count=result.page_count,
                    )
                else:
                    console.print(
                        f"[red]Both extractors failed for {pdf.name}[/red] - content may be unusable"
                    )

            # Save markdown
            md_path = md_dir / f"{pdf.stem}.md"
            md_path.write_text(result.markdown, encoding="utf-8")

            # Save tables as JSON
            tables_path = tables_dir / f"{pdf.stem}.json"
            tables_data = [
                {"page": t.page, "data": t.data, "caption": t.caption} for t in result.tables
            ]
            tables_path.write_text(json.dumps(tables_data, indent=2, ensure_ascii=False))

            # Save figures metadata as JSON
            figures_path = None
            if result.figures:
                figures_path = figures_base_dir / f"{pdf.stem}.json"
                figures_data = [
                    {"page": f.page, "image_path": f.image_path, "caption": f.caption}
                    for f in result.figures
                ]
                figures_path.write_text(json.dumps(figures_data, indent=2, ensure_ascii=False))

            # Update inventory
            inventory.add_paper(
                paper_id=pdf.stem,
                filename=pdf.name,
                markdown_path=md_path,
                tables_path=tables_path,
                figures_path=figures_path,
                status="ingested",
            )
            success_count += 1

        except Exception as e:
            console.print(f"[red]Error processing {pdf.name}:[/red] {e}")
            inventory.add_paper(
                paper_id=pdf.stem,
                filename=pdf.name,
                status="failed",
            )
            error_count += 1

    # Save inventory
    inventory.save(project_dir)

    # Summary
    console.print()
    console.print(f"[green]Successfully ingested:[/green] {success_count} papers")
    if error_count:
        console.print(f"[red]Failed:[/red] {error_count} papers")
    console.print(f"[dim]Markdown saved to:[/dim] {md_dir}")
    console.print(f"[dim]Tables saved to:[/dim] {tables_dir}")
    console.print(f"[dim]Figures saved to:[/dim] {figures_base_dir}")
