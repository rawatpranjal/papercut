"""Output renderers for reports."""

from papercut.report.renderers.markdown import render_markdown
from papercut.report.renderers.json_renderer import render_json
from papercut.report.renderers.latex import render_latex
from papercut.report.renderers.pdf import render_pdf

__all__ = ["render_markdown", "render_json", "render_latex", "render_pdf"]
