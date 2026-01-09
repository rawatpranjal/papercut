"""Report builder for Papercutter Factory.

Generates LaTeX and Markdown reports from extraction results
using Jinja2 templates.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from papercutter.grinding.matrix import ExtractionMatrix, PaperExtraction
from papercutter.grinding.schema import ExtractionSchema
from papercutter.utils.bibtex import BibTeXEntry

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Output format for reports."""

    LATEX = "latex"
    MARKDOWN = "markdown"


@dataclass
class ReportContext:
    """Context data for report generation."""

    # Project metadata
    title: str = "Systematic Review"
    author: str = ""
    date: str = ""
    abstract: str = ""

    # Data
    matrix: ExtractionMatrix | None = None
    schema: ExtractionSchema | None = None
    bibliography: list[BibTeXEntry] = field(default_factory=list)

    # Options
    include_summaries: bool = True
    include_matrix: bool = True
    include_appendix: bool = True
    bibliography_style: str = "apa"

    @property
    def papers(self) -> list[PaperExtraction]:
        """Get list of paper extractions."""
        if self.matrix:
            return list(self.matrix)
        return []

    @property
    def paper_count(self) -> int:
        """Number of papers in the review."""
        return len(self.papers)

    @property
    def fields(self) -> list[dict[str, Any]]:
        """Get schema fields as dicts."""
        if self.schema:
            return [f.to_dict() for f in self.schema.fields]
        return []


class ReportBuilder:
    """Builds reports from extraction results using Jinja2 templates.

    Supports LaTeX and Markdown output formats with customizable templates.
    """

    # Default template directory (relative to this module)
    DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"

    def __init__(
        self,
        template_dir: Path | None = None,
        output_format: ReportFormat = ReportFormat.LATEX,
    ):
        """Initialize the builder.

        Args:
            template_dir: Custom template directory.
            output_format: Output format (latex or markdown).
        """
        self.template_dir = template_dir or self.DEFAULT_TEMPLATE_DIR
        self.output_format = output_format
        self._env = None

    def _get_env(self):
        """Get or create Jinja2 environment."""
        if self._env is not None:
            return self._env

        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
        except ImportError:
            raise ImportError(
                "jinja2 is required for report generation. "
                "Install with: pip install jinja2"
            )

        # Configure for LaTeX (different delimiters to avoid conflicts)
        if self.output_format == ReportFormat.LATEX:
            self._env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=False,  # Don't escape for LaTeX
                block_start_string="<%",
                block_end_string="%>",
                variable_start_string="<<",
                variable_end_string=">>",
                comment_start_string="<#",
                comment_end_string="#>",
            )
            # Add LaTeX-safe filters
            self._env.filters["latex_escape"] = self._latex_escape
        else:
            self._env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(["html", "xml"]),
            )

        # Add common filters
        self._env.filters["truncate_chars"] = self._truncate_chars

        return self._env

    def build(
        self,
        context: ReportContext,
        template_name: str | None = None,
        output_path: Path | None = None,
    ) -> str:
        """Build a report from context data.

        Args:
            context: Report context with data.
            template_name: Template file name (defaults based on format).
            output_path: Optional path to save the report.

        Returns:
            Rendered report as string.
        """
        env = self._get_env()

        # Select template
        if template_name is None:
            if self.output_format == ReportFormat.LATEX:
                template_name = "default.tex.j2"
            else:
                template_name = "default.md.j2"

        try:
            template = env.get_template(template_name)
        except Exception:
            logger.warning(f"Template {template_name} not found, using built-in")
            # Use built-in template
            content = self._get_builtin_template()
            template = env.from_string(content)

        # Prepare template data
        data = self._prepare_context(context)

        # Render
        rendered = template.render(**data)

        # Save if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered)
            logger.info(f"Report saved to {output_path}")

        return rendered

    def _prepare_context(self, context: ReportContext) -> dict[str, Any]:
        """Prepare context data for template."""
        # Build paper data with extractions
        papers_data = []
        for paper in context.papers:
            paper_dict = {
                "id": paper.paper_id,
                "title": paper.title or "Untitled",
                "bibtex_key": paper.bibtex_key,
                "one_pager": paper.one_pager,
                "appendix_row": paper.appendix_row,
                "extractions": {},
            }
            for key, value in paper.extractions.items():
                paper_dict["extractions"][key] = {
                    "value": value.value,
                    "quote": value.source_quote,
                    "page": value.page_number,
                }
            papers_data.append(paper_dict)

        # Build matrix data for table
        matrix_data = []
        if context.matrix and context.schema:
            header = ["Paper"] + [f.key for f in context.schema.fields]
            matrix_data.append(header)

            for paper in context.papers:
                row = [paper.title or paper.paper_id]
                for f in context.schema.fields:
                    val = paper.get_value(f.key)
                    row.append(str(val) if val is not None else "N/A")
                matrix_data.append(row)

        return {
            "title": context.title,
            "author": context.author,
            "date": context.date,
            "abstract": context.abstract,
            "paper_count": context.paper_count,
            "papers": papers_data,
            "fields": context.fields,
            "matrix": matrix_data,
            "bibliography": [b.to_dict() for b in context.bibliography],
            "include_summaries": context.include_summaries,
            "include_matrix": context.include_matrix,
            "include_appendix": context.include_appendix,
            "bibliography_style": context.bibliography_style,
        }

    def _get_builtin_template(self) -> str:
        """Get built-in template string."""
        if self.output_format == ReportFormat.LATEX:
            return BUILTIN_LATEX_TEMPLATE
        else:
            return BUILTIN_MARKDOWN_TEMPLATE

    @staticmethod
    def _latex_escape(text: str) -> str:
        """Escape special LaTeX characters."""
        if not text:
            return ""

        # Characters that need escaping in LaTeX
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

        for char, replacement in replacements:
            text = text.replace(char, replacement)

        return text

    @staticmethod
    def _truncate_chars(text: str, length: int, suffix: str = "...") -> str:
        """Truncate text to specified length."""
        if not text or len(text) <= length:
            return text or ""
        return text[: length - len(suffix)] + suffix


# Built-in LaTeX template
BUILTIN_LATEX_TEMPLATE = r"""% Systematic Review Report
% Generated by Papercutter Factory

\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{parskip}

\geometry{margin=1in}

\title{<< title | latex_escape >>}
\author{<< author | latex_escape >>}
\date{<< date >>}

\begin{document}

\maketitle

<% if abstract %>
\begin{abstract}
<< abstract | latex_escape >>
\end{abstract}
<% endif %>

\section{Introduction}

This systematic review includes << paper_count >> papers.

<% if include_matrix and matrix %>
\section{Evidence Matrix}

\begin{longtable}{<% for _ in matrix[0] %>l<% endfor %>}
\toprule
<% for cell in matrix[0] %><< cell | latex_escape >><% if not loop.last %> & <% endif %><% endfor %> \\
\midrule
\endhead
<% for row in matrix[1:] %>
<% for cell in row %><< cell | latex_escape | truncate_chars(50) >><% if not loop.last %> & <% endif %><% endfor %> \\
<% endfor %>
\bottomrule
\end{longtable}
<% endif %>

<% if include_summaries %>
\section{Paper Summaries}

<% for paper in papers %>
\subsection{<< paper.title | latex_escape >>}

<% if paper.one_pager %>
<< paper.one_pager | latex_escape >>
<% else %>
No summary available.
<% endif %>

<% endfor %>
<% endif %>

<% if include_appendix %>
\appendix
\section{Paper Contributions}

\begin{enumerate}
<% for paper in papers %>
\item \textbf{<< paper.title | latex_escape | truncate_chars(60) >>}: << paper.appendix_row | latex_escape if paper.appendix_row else 'No contribution statement.' >>
<% endfor %>
\end{enumerate}
<% endif %>

\end{document}
"""

# Built-in Markdown template
BUILTIN_MARKDOWN_TEMPLATE = """# {{ title }}

{% if author %}**Author:** {{ author }}{% endif %}
{% if date %}**Date:** {{ date }}{% endif %}

{% if abstract %}
## Abstract

{{ abstract }}
{% endif %}

## Introduction

This systematic review includes {{ paper_count }} papers.

{% if include_matrix and matrix %}
## Evidence Matrix

| {% for cell in matrix[0] %}{{ cell }}{% if not loop.last %} | {% endif %}{% endfor %} |
|{% for _ in matrix[0] %}---|{% endfor %}
{% for row in matrix[1:] %}
| {% for cell in row %}{{ cell | truncate_chars(50) }}{% if not loop.last %} | {% endif %}{% endfor %} |
{% endfor %}
{% endif %}

{% if include_summaries %}
## Paper Summaries

{% for paper in papers %}
### {{ paper.title }}

{% if paper.one_pager %}
{{ paper.one_pager }}
{% else %}
*No summary available.*
{% endif %}

{% endfor %}
{% endif %}

{% if include_appendix %}
## Appendix: Paper Contributions

{% for paper in papers %}
{{ loop.index }}. **{{ paper.title | truncate_chars(60) }}**: {{ paper.appendix_row if paper.appendix_row else '*No contribution statement.*' }}
{% endfor %}
{% endif %}

---
*Generated by Papercutter Factory*
"""


def build_report(
    matrix: ExtractionMatrix,
    output_path: Path,
    title: str = "Systematic Review",
    output_format: ReportFormat = ReportFormat.LATEX,
    **kwargs: Any,
) -> str:
    """Convenience function to build a report.

    Args:
        matrix: Extraction matrix with data.
        output_path: Path to save the report.
        title: Report title.
        output_format: Output format (latex or markdown).
        **kwargs: Additional context options.

    Returns:
        Rendered report string.
    """
    context = ReportContext(
        title=title,
        matrix=matrix,
        schema=matrix.schema,
        **kwargs,
    )

    builder = ReportBuilder(output_format=output_format)
    return builder.build(context, output_path=output_path)
