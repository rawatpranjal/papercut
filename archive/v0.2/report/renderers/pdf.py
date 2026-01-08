"""PDF renderer for reports (via pandoc)."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from papercutter.exceptions import PapercutterError
from papercutter.report.generator import Report


def check_pandoc_available() -> bool:
    """Check if pandoc is installed.

    Returns:
        True if pandoc is available.
    """
    return shutil.which("pandoc") is not None


def render_pdf(
    report: Report,
    output_path: Path,
    title: Optional[str] = None,
) -> Path:
    """Render report as PDF using pandoc.

    Args:
        report: Report object.
        output_path: Output PDF path.
        title: Optional document title.

    Returns:
        Path to generated PDF.

    Raises:
        PapercutterError: If pandoc is not available or conversion fails.
    """
    if not check_pandoc_available():
        raise PapercutterError(
            "PDF output requires pandoc",
            details="Install pandoc: https://pandoc.org/installing.html",
        )

    output_path = Path(output_path)

    # Prepare title
    if not title:
        title = report.source_path.stem.replace("_", " ").title()

    # Create temporary markdown file with YAML frontmatter
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(f"""---
title: "{title}"
date: \\today
geometry: margin=1in
---

{report.content}
""")
        temp_md = Path(f.name)

    try:
        # Run pandoc
        cmd = [
            "pandoc",
            str(temp_md),
            "-o",
            str(output_path),
            "--pdf-engine=pdflatex",
            "-V",
            "colorlinks=true",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Try with xelatex if pdflatex fails
            cmd[4] = "--pdf-engine=xelatex"
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise PapercutterError(
                    "PDF conversion failed",
                    details=result.stderr or result.stdout,
                )

        return output_path

    finally:
        # Clean up temp file
        temp_md.unlink(missing_ok=True)
