"""JSON renderer for reports."""

import json
from typing import Any

from papercut.report.generator import Report


def render_json(report: Report) -> str:
    """Render report as JSON.

    Args:
        report: Report object.

    Returns:
        JSON formatted string.
    """
    # Try to parse content as JSON if it's from a structured template
    try:
        content_data = json.loads(report.content)
    except json.JSONDecodeError:
        # Content is not JSON, wrap it
        content_data = {"content": report.content}

    output: dict[str, Any] = {
        "source": str(report.source_path),
        "template": report.template,
        "metadata": report.metadata,
        "data": content_data,
    }

    return json.dumps(output, indent=2, ensure_ascii=False)
