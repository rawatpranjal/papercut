"""Markdown renderer for reports."""

from papercutter.report.generator import Report


def render_markdown(report: Report) -> str:
    """Render report as Markdown.

    Args:
        report: Report object.

    Returns:
        Markdown formatted string.
    """
    # Report content is already markdown from the LLM
    # Add metadata header
    header = f"""---
source: {report.source_path.name}
template: {report.template}
model: {report.metadata.get('model', 'unknown')}
---

"""
    return header + report.content
