"""Equation extraction command."""

from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from papercutter.cli.extract import parse_pages
from papercutter.cli.utils import handle_errors, is_quiet
from papercutter.output import get_formatter

if TYPE_CHECKING:
    from papercutter.converters.base import BaseConverter

# Available conversion methods
METHODS = ["none", "nougat", "pix2tex", "mathpix"]


def _validate_pdf_path(pdf_path: Path) -> None:
    """Validate that a PDF path exists and is a file."""
    if not pdf_path.exists():
        raise typer.BadParameter(f"PDF file not found: {pdf_path}")
    if not pdf_path.is_file():
        raise typer.BadParameter(f"Not a file: {pdf_path}")


def _get_console() -> Console:
    """Get a console for output messages."""
    return Console()


def _get_converter(method: str) -> "BaseConverter | None":
    """Get the appropriate converter for the method.

    Args:
        method: Conversion method name.

    Returns:
        Converter instance or None.

    Raises:
        ImportError: If the required converter is not available.
    """
    if method == "none":
        return None

    if method == "nougat":
        from papercutter.converters.nougat import NougatConverter

        nougat_conv = NougatConverter()
        if not nougat_conv.is_available():
            raise ImportError(
                "Nougat is not installed. Install with: pip install 'papercutter[equations-nougat]'"
            )
        # Note: Model download warning is handled in NougatConverter._ensure_model()
        return nougat_conv

    if method == "pix2tex":
        from papercutter.converters.pix2tex import Pix2TexConverter

        pix2tex_conv = Pix2TexConverter()
        if not pix2tex_conv.is_available():
            raise ImportError(
                "pix2tex is not installed. Install with: pip install 'papercutter[equations-pix2tex]'"
            )
        return pix2tex_conv

    if method == "mathpix":
        from papercutter.converters.mathpix import MathPixConverter

        mathpix_conv = MathPixConverter()
        if not mathpix_conv.is_available():
            raise ImportError(
                "MathPix API keys not configured. "
                "Set PAPERCUTTER_MATHPIX_APP_ID and PAPERCUTTER_MATHPIX_APP_KEY"
            )
        return mathpix_conv

    return None


@handle_errors
def equations(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for equation images",
    ),
    pages: str | None = typer.Option(
        None,
        "--pages",
        "-p",
        help="Page range to extract (e.g., '40-50')",
    ),
    no_latex: bool = typer.Option(
        False,
        "--no-latex",
        help="Skip LaTeX conversion (faster, images only)",
    ),
    method: str = typer.Option(
        "nougat",
        "--method",
        "-m",
        help="LaTeX conversion method: none, nougat, pix2tex, or mathpix",
    ),
    min_confidence: float = typer.Option(
        0.0,
        "--min-confidence",
        help="Minimum confidence threshold for LaTeX (0.0-1.0)",
    ),
    verify: bool = typer.Option(
        False,
        "--verify",
        help="Show warnings for low-confidence conversions",
    ),
    detect_inline: bool = typer.Option(
        True,
        "--detect-inline/--no-detect-inline",
        help="Whether to detect inline equations",
    ),
    dpi: int = typer.Option(
        300,
        "--dpi",
        help="DPI for equation images",
    ),
    use_json: bool = typer.Option(
        False,
        "--json",
        help="Force JSON output",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Force pretty output",
    ),
):
    """Extract equations from PDF.

    Detects mathematical equations and extracts them as high-resolution
    PNG images. Optionally converts to LaTeX using Nougat (default),
    pix2tex, or MathPix.

    Examples:

        papercutter equations textbook.pdf

        papercutter equations textbook.pdf --pages 40-50

        papercutter equations textbook.pdf --no-latex

        papercutter equations textbook.pdf --method pix2tex

        papercutter equations textbook.pdf --min-confidence 0.9 --verify
    """
    from papercutter.cache import get_cache
    from papercutter.core.equations import EquationExtractor

    _validate_pdf_path(pdf_path)

    console = _get_console()
    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())
    cache = get_cache()

    # Validate method
    if method not in METHODS:
        raise typer.BadParameter(f"Invalid method: {method}. Choose from: {', '.join(METHODS)}")

    # Validate confidence threshold
    if not 0.0 <= min_confidence <= 1.0:
        raise typer.BadParameter("min-confidence must be between 0.0 and 1.0")

    # Validate DPI
    if dpi < 72 or dpi > 600:
        raise typer.BadParameter("dpi must be between 72 and 600")

    # Get converter if LaTeX conversion requested
    converter = None
    if not no_latex and method != "none":
        try:
            converter = _get_converter(method)
        except ImportError as e:
            # Fall back to no converter with warning
            if not is_quiet():
                console.print(f"[yellow]Warning:[/yellow] {e}")
                console.print("[dim]Proceeding with image-only extraction[/dim]")
            converter = None

    # Create extractor
    extractor = EquationExtractor(
        converter=converter,
        dpi=dpi,
        detect_inline=detect_inline,
    )

    # Check availability
    if not extractor.is_available():
        result = {
            "success": False,
            "error": "PyMuPDF required for equation extraction",
            "hint": "Install with: pip install pymupdf",
        }
        formatter.output(result)
        raise typer.Exit(1)

    # Parse pages
    page_list = parse_pages(pages)

    # Extract equations
    extraction_result = extractor.extract(
        pdf_path,
        pages=page_list,
        extract_latex=not no_latex and converter is not None,
        min_confidence=min_confidence,
    )

    # Save images if output directory specified
    if output:
        output.mkdir(parents=True, exist_ok=True)
        for eq in extraction_result.equations:
            img_path = output / f"eq_{eq.id:03d}_p{eq.page}.png"
            eq.save(img_path)
        if not is_quiet():
            console.print(
                f"[green]Saved {len(extraction_result.equations)} equation(s) to:[/green] {output}"
            )
    else:
        # Cache images
        for eq in extraction_result.equations:
            cached_path = cache.set_equation(pdf_path, eq.id, eq.image_data)
            eq.image_path = cached_path

    # Build result
    requested_method = method if not no_latex and method != "none" else None
    result = {
        "success": True,
        "file": str(pdf_path.name),
        "requested_method": requested_method,
        "method_available": converter is not None if requested_method else None,
        **extraction_result.to_dict(),
    }

    # Show verification warnings if requested
    if verify:
        low_conf = [eq for eq in extraction_result.equations if eq.is_low_confidence]
        if low_conf and not is_quiet():
            console.print(
                f"\n[yellow]Warning:[/yellow] {len(low_conf)} equation(s) with low confidence:"
            )
            for eq in low_conf[:5]:
                conf = eq.latex.confidence if eq.latex else 0
                console.print(f"  - Equation #{eq.id} (page {eq.page}): {conf:.1%} confidence")
            if len(low_conf) > 5:
                console.print(f"  ... and {len(low_conf) - 5} more")

    formatter.output(result)


@handle_errors
def equation(
    pdf_path: Path = typer.Argument(..., help="Path to PDF file"),
    equation_id: int = typer.Option(
        ...,
        "--id",
        "-i",
        help="Equation ID to extract",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path for equation image",
    ),
    use_json: bool = typer.Option(
        False,
        "--json",
        help="Force JSON output",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Force pretty output",
    ),
):
    """Extract a single equation by ID.

    Returns path to cached equation or saves to specified output.
    """
    from papercutter.cache import get_cache
    from papercutter.core.equations import EquationExtractor

    _validate_pdf_path(pdf_path)

    formatter = get_formatter(json_flag=use_json, pretty_flag=pretty, quiet=is_quiet())
    cache = get_cache()

    # Check cache first
    cached_path = cache.get_equation_path(pdf_path, equation_id)
    if cached_path:
        if output:
            import shutil

            shutil.copy(cached_path, output)
            result = {"success": True, "file": str(pdf_path.name), "equation_path": str(output)}
        else:
            result = {
                "success": True,
                "cached": True,
                "file": str(pdf_path.name),
                "equation_path": str(cached_path),
            }
        formatter.output(result)
        return

    # Extract equation
    try:
        extractor = EquationExtractor()
        extraction_result = extractor.extract(pdf_path, extract_latex=False)

        if equation_id < 1 or equation_id > len(extraction_result.equations):
            result = {
                "success": False,
                "error": (
                    f"Equation {equation_id} not found. "
                    f"Document has {len(extraction_result.equations)} equation(s)."
                ),
            }
            formatter.output(result)
            raise typer.Exit(1)

        eq = extraction_result.equations[equation_id - 1]

        # Save to cache or output
        if output:
            eq.save(output)
            eq_path = str(output)
        else:
            eq_path = str(cache.set_equation(pdf_path, equation_id, eq.image_data))

        result = {
            "success": True,
            "file": str(pdf_path.name),
            "equation": eq.to_dict(),
            "equation_path": eq_path,
        }
        formatter.output(result)

    except ImportError as e:
        result = {"success": False, "error": str(e)}
        formatter.output(result)
        raise typer.Exit(1) from None
