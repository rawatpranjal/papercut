"""LaTeX renderer for reports."""

from papercutter.report.generator import Report


def render_latex(report: Report) -> str:
    """Render report as LaTeX snippet.

    Args:
        report: Report object.

    Returns:
        LaTeX formatted string (snippet, not full document).
    """
    # If report was already generated as latex, return as-is
    if report.format == "latex":
        return report.content

    # Otherwise convert markdown to latex
    return _markdown_to_latex(report.content)


def _markdown_to_latex(content: str) -> str:
    """Convert markdown to LaTeX.

    Args:
        content: Markdown text.

    Returns:
        LaTeX text.
    """
    import re

    result = content

    # Escape special LaTeX characters (except those we'll convert)
    # Do this first before adding LaTeX commands
    for char in ["&", "%", "$", "#", "_"]:
        result = result.replace(char, "\\" + char)

    # Convert headers
    result = re.sub(r"^### (.+)$", r"\\subsubsection*{\1}", result, flags=re.MULTILINE)
    result = re.sub(r"^## (.+)$", r"\\subsection*{\1}", result, flags=re.MULTILINE)
    result = re.sub(r"^# (.+)$", r"\\section*{\1}", result, flags=re.MULTILINE)

    # Convert bold and italic
    result = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", result)
    result = re.sub(r"\*(.+?)\*", r"\\textit{\1}", result)

    # Convert bullet points to itemize
    lines = result.split("\n")
    output_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if not in_list:
                output_lines.append("\\begin{itemize}")
                in_list = True
            output_lines.append("  \\item " + stripped[2:])
        else:
            if in_list and stripped:
                output_lines.append("\\end{itemize}")
                in_list = False
            output_lines.append(line)

    if in_list:
        output_lines.append("\\end{itemize}")

    return "\n".join(output_lines)


def render_latex_document(report: Report, title: str = "") -> str:
    """Render report as a complete LaTeX document.

    Args:
        report: Report object.
        title: Document title.

    Returns:
        Complete LaTeX document.
    """
    snippet = render_latex(report)

    if not title:
        title = report.source_path.stem.replace("_", " ").title()

    document = f"""\\documentclass{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{hyperref}}
\\usepackage{{geometry}}
\\geometry{{margin=1in}}

\\title{{{title}}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle

{snippet}

\\end{{document}}
"""
    return document
