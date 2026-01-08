"""Output renderers for reports."""

from papercutter.report.renderers.markdown import render_markdown
from papercutter.report.renderers.json_renderer import render_json
from papercutter.report.renderers.latex import render_latex
from papercutter.report.renderers.pdf import render_pdf

__all__ = ["render_markdown", "render_json", "render_latex", "render_pdf"]
