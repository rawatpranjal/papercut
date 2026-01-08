"""Prompt templates for LLM-powered features.

Templates are loaded lazily from external files to reduce memory usage.
"""

from functools import lru_cache
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "templates"


@lru_cache(maxsize=32)
def _load_template(name: str) -> str:
    """Load a template by name (without extension)."""
    template_path = TEMPLATE_DIR / f"{name}.txt"
    return template_path.read_text()


def get_summarize_prompt(
    content: str,
    focus: str | None = None,
    length: str = "default",
) -> tuple[str, str]:
    """Get the appropriate summarize prompt."""
    system_prompt = _load_template("system_summarize")

    if focus:
        template = _load_template("summarize_focused")
        prompt = template.format(content=content, focus=focus)
    elif length == "short":
        template = _load_template("summarize_short")
        prompt = template.format(content=content)
    elif length == "long":
        template = _load_template("summarize_long")
        prompt = template.format(content=content)
    else:
        template = _load_template("summarize_default")
        prompt = template.format(content=content)

    return system_prompt, prompt


def get_report_prompt(
    content: str,
    template: str,
) -> tuple[str, str]:
    """Get the appropriate report prompt."""
    system_prompt = _load_template("system_report")

    template_files = {
        "reading-group": "report_reading_group",
        "referee": "report_referee",
        "meta": "report_meta",
        "executive": "report_executive",
    }
    template_name = template_files.get(template, "report_reading_group")
    template_content = _load_template(template_name)
    prompt = template_content.format(content=content)

    return system_prompt, prompt


def get_study_prompt(
    content: str,
    mode: str,
) -> tuple[str, str]:
    """Get the appropriate study prompt."""
    system_prompt = _load_template("system_study")

    mode_files = {
        "summary": "study_summary",
        "concepts": "study_concepts",
        "quiz": "study_quiz",
        "flashcards": "study_flashcards",
    }
    template_name = mode_files.get(mode, "study_summary")
    template_content = _load_template(template_name)
    prompt = template_content.format(content=content)

    return system_prompt, prompt


def clear_template_cache() -> None:
    """Clear the template cache (useful in tests)."""
    _load_template.cache_clear()
