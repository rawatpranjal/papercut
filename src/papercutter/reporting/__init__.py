"""Reporting pipeline for Papercutter Factory.

This module handles report generation from extraction results:
1. LaTeX report generation using Jinja2 templates
2. Markdown report generation
3. Bibliography integration
"""

from papercutter.reporting.builder import (
    ReportBuilder,
    ReportContext,
    ReportFormat,
    build_report,
)

__all__ = [
    "ReportBuilder",
    "ReportContext",
    "ReportFormat",
    "build_report",
]
