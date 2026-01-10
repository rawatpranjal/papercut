"""Generate matrix.csv and review.pdf from extraction results."""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


def _check_jinja2() -> bool:
    """Check if Jinja2 is available."""
    try:
        import jinja2  # noqa: F401

        return True
    except ImportError:
        return False


def latex_escape(text: Any) -> str:
    """Escape special LaTeX characters."""
    if text is None:
        return ""
    text = str(text)
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for char, repl in replacements:
        text = text.replace(char, repl)
    return text


def markdown_to_latex(text: Any) -> str:
    """Convert markdown bold/italic to LaTeX and escape special chars."""
    import re
    if text is None:
        return ""
    text = str(text)

    # First convert markdown to LaTeX BEFORE escaping
    # **bold** -> \textbf{bold}
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    # *italic* -> \textit{italic}
    text = re.sub(r'\*(.+?)\*', r'\\textit{\1}', text)

    # Now escape remaining special chars (but not the LaTeX we just created)
    # Only escape chars that aren't part of our LaTeX commands
    replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("~", r"\textasciitilde{}"),
    ]
    for char, repl in replacements:
        text = text.replace(char, repl)
    return text


def preserve_latex_math(text: Any) -> str:
    """Escape special chars but preserve LaTeX math mode ($...$).

    For technical fields (method, results, notation) where LLM outputs
    inline LaTeX math that should render correctly.
    """
    import re
    if text is None:
        return ""
    text = str(text)

    # First, escape currency amounts like $400, $2 trillion, etc.
    # These are $ followed by a digit - definitely not math
    text = re.sub(r'\$(\d)', r'\\$\1', text)

    # Split on math delimiters (both $...$ and $$...$$)
    # This regex captures math blocks so they appear in the split result
    parts = re.split(r'(\$\$[^$]+\$\$|\$[^$]+\$)', text)

    result = []
    for part in parts:
        if (part.startswith('$$') and part.endswith('$$')) or \
           (part.startswith('$') and part.endswith('$') and len(part) > 2):
            # Math mode - keep as-is
            result.append(part)
        else:
            # Normal text - escape special chars (but not \ which is used in LaTeX)
            for char, repl in [("&", r"\&"), ("%", r"\%"), ("#", r"\#")]:
                part = part.replace(char, repl)
            result.append(part)

    return ''.join(result)


def truncate(text: str, length: int = 50) -> str:
    """Truncate text at word boundary."""
    if not text or len(text) <= length:
        return text or ""
    truncated = text[:length]
    last_space = truncated.rfind(" ")
    if last_space > length // 2:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "..."


def build_report() -> None:
    """Generate matrix.csv and review.pdf from extractions."""
    project_dir = Path.cwd()

    # Load extractions
    extractions_path = project_dir / "extractions.json"
    if not extractions_path.exists():
        console.print("[red]Error:[/red] No extractions.json found. Run 'papercutter grind' first.")
        return

    data = json.loads(extractions_path.read_text(encoding="utf-8"))

    # Handle both old format (list) and new format (dict with executive_summary)
    if isinstance(data, list):
        extractions = data
        executive_summary = None
    else:
        executive_summary = data.get("executive_summary")
        extractions = data.get("papers", [])

    if not extractions:
        console.print("[yellow]Warning:[/yellow] No extractions to report")
        return

    # Create output directory
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Build CSV
    csv_path = output_dir / "matrix.csv"
    build_csv(extractions, csv_path)

    # Build PDF
    pdf_path = output_dir / "review.pdf"
    build_pdf(extractions, pdf_path, executive_summary=executive_summary)

    console.print()
    console.print("[bold green]Report complete![/bold green]")
    console.print(f"  CSV:  {csv_path}")
    console.print(f"  PDF:  {pdf_path}")


def build_csv(extractions: list[dict], output_path: Path) -> None:
    """Export flat CSV matrix."""
    if not extractions:
        console.print("[yellow]No extractions to export to CSV[/yellow]")
        return

    # Collect all data field keys
    all_keys: set[str] = set()
    for e in extractions:
        all_keys.update(e.get("data", {}).keys())

    fieldnames = ["paper_id", "title", *sorted(all_keys)]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for e in extractions:
            row = {
                "paper_id": e.get("paper_id", ""),
                "title": e.get("title", ""),
            }
            row.update(e.get("data", {}))
            writer.writerow(row)

    console.print(f"[green]CSV saved:[/green] {output_path}")


def build_pdf(
    extractions: list[dict], output_path: Path, executive_summary: str | None = None
) -> None:
    """Generate LaTeX dossier and compile to PDF."""
    if not _check_jinja2():
        console.print("[yellow]Warning:[/yellow] Jinja2 not installed. Skipping PDF generation.")
        console.print("[dim]Install with: pip install papercutter[report][/dim]")
        return

    from jinja2 import Environment, FileSystemLoader

    # Load template
    template_dir = Path(__file__).parent / "templates"

    # Create environment with filters FIRST
    if template_dir.exists():
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="<<",
            variable_end_string=">>",
        )
    else:
        env = Environment(
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="<<",
            variable_end_string=">>",
        )

    # Add filters BEFORE loading template
    env.filters["latex_escape"] = latex_escape
    env.filters["markdown_to_latex"] = markdown_to_latex
    env.filters["preserve_latex_math"] = preserve_latex_math
    env.filters["truncate"] = truncate

    # Now load template
    if template_dir.exists():
        try:
            template = env.get_template("review.tex.j2")
        except Exception:
            console.print("[dim]Using built-in template[/dim]")
            template = env.from_string(BUILTIN_TEMPLATE)
    else:
        console.print("[dim]Using built-in template[/dim]")
        template = env.from_string(BUILTIN_TEMPLATE)

    # Get all data keys for the matrix header
    all_data_keys: list[str] = []
    if extractions and extractions[0].get("data"):
        all_data_keys = sorted(extractions[0]["data"].keys())

    # Render template
    rendered = template.render(
        title="Literature Review",
        executive_summary=executive_summary,
        paper_count=len(extractions),
        papers=extractions,
        data_keys=all_data_keys,
    )

    # Write .tex file
    tex_path = output_path.with_suffix(".tex")
    tex_path.write_text(rendered, encoding="utf-8")
    console.print(f"[dim]LaTeX saved:[/dim] {tex_path}")

    # Try to compile PDF
    try:
        # Run pdflatex twice for proper references
        for _ in range(2):
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                cwd=output_path.parent,
                capture_output=True,
                timeout=120,
            )

        if output_path.exists():
            console.print(f"[green]PDF saved:[/green] {output_path}")
        else:
            console.print("[yellow]Warning:[/yellow] PDF compilation may have failed")
            console.print(f"[dim]Check {tex_path} and compile manually[/dim]")

        # Clean up auxiliary files
        for ext in [".aux", ".log", ".out"]:
            aux_file = output_path.with_suffix(ext)
            if aux_file.exists():
                aux_file.unlink()

    except FileNotFoundError:
        console.print("[yellow]Warning:[/yellow] pdflatex not found. PDF not compiled.")
        console.print("[dim]Install a LaTeX distribution to compile the PDF[/dim]")
    except subprocess.TimeoutExpired:
        console.print("[yellow]Warning:[/yellow] PDF compilation timed out")
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] PDF compilation failed: {e}")


BUILTIN_TEMPLATE = r"""\documentclass[10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[margin=0.75in]{geometry}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{parskip}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{amsmath}
\usepackage{pdflscape}
\usepackage{tabularx}
\usepackage{graphicx}

\definecolor{accent}{HTML}{0891B2}
\definecolor{lightgray}{HTML}{6B7280}

\hypersetup{colorlinks=true, linkcolor=accent, urlcolor=accent}

\titleformat{\section}{\large\bfseries}{}{0em}{}
\titlespacing*{\section}{0pt}{1.5ex}{0.5ex}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textcolor{lightgray}{Literature Review}}
\fancyhead[R]{\small\textcolor{lightgray}{\today}}
\fancyfoot[C]{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\setlength{\parskip}{0.4em}
\setlist[itemize]{nosep, leftmargin=1.5em}

\title{\textbf{<< title | latex_escape >>}}
\author{}
\date{<< paper_count >> papers analyzed $\cdot$ \today}

\begin{document}

\maketitle
\thispagestyle{empty}

<% if executive_summary %>
\section*{Executive Summary}
\addcontentsline{toc}{section}{Executive Summary}

<< executive_summary | latex_escape >>

\newpage
<% endif %>

\tableofcontents
\newpage

<% for paper in papers %>
\section{<< paper.title | latex_escape | truncate(75) >>}
\textit{<< paper.authors | latex_escape >>} (<< paper.year | latex_escape >>) \hfill \textsc{\small << paper.paper_type | latex_escape >>}

\vspace{0.3em}\hrule\vspace{0.8em}

\textbf{Context.} << paper.context | latex_escape >>

<% if paper.golden_quote %>
\begin{quote}
\textit{``<< paper.golden_quote | latex_escape >>''}
\end{quote}
<% endif %>

<% if paper.prior_work %>\textbf{Prior Work.} << paper.prior_work | latex_escape >>

<% endif %>\textbf{Method.} << paper.method | latex_escape >>

<% if paper.key_equations %>\textbf{Key Equation.} << paper.key_equations >>
<% if paper.notation %>\\textit{where << paper.notation | latex_escape >>}
<% endif %>

<% endif %>\textbf{Results.} << paper.results | latex_escape >>

<% if paper.key_visual_explanation %>
\vspace{0.5em}
\textbf{Key Visual} (<< paper.key_figure_ref | latex_escape >>). << paper.key_visual_explanation | latex_escape >>
<% if paper.key_visual_path %>
\begin{figure}[h]
\centering
\includegraphics[width=0.7\textwidth]{<< paper.key_visual_path >>}
\caption{<< paper.key_figure_description | latex_escape >>}
\end{figure}
<% endif %>
<% endif %>

<% if paper.data_description %>\textbf{Data.} << paper.data_description | latex_escape >>

<% endif %><% if paper.contribution %>\textbf{Contribution.} << paper.contribution | latex_escape >>

<% endif %><% if paper.applications %>\textbf{Applications.} << paper.applications | latex_escape >>

<% endif %><% if paper.limitations %>\textbf{Limitations.} << paper.limitations | latex_escape >>

<% endif %>\newpage
<% endfor %>

\end{document}
"""
