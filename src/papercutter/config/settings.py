"""Pydantic settings for Papercutter configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_config_dir() -> Path:
    """Get the configuration directory, creating it if needed."""
    config_dir = Path.home() / ".papercutter"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_config_dir() / "config.yaml"


def _load_yaml_config() -> dict[str, Any]:
    """Load configuration from YAML file if it exists.

    Returns:
        Dictionary of configuration values, or empty dict if file doesn't exist.
    """
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError):
            # Silently ignore malformed or unreadable config
            return {}
    return {}


class TextExtractionSettings(BaseModel):
    """Settings for text extraction."""

    chunk_size: int | None = None
    chunk_overlap: int = 200


class TableExtractionSettings(BaseModel):
    """Settings for table extraction."""

    format: str = "csv"


class EquationExtractionSettings(BaseModel):
    """Settings for equation extraction."""

    method: str = "nougat"  # nougat, pix2tex, mathpix
    min_confidence: float = 0.0
    image_dpi: int = 300
    detect_inline: bool = True
    min_width: int = 50
    min_height: int = 20


class ExtractionSettings(BaseModel):
    """Settings for content extraction."""

    backend: str = "pdfplumber"
    text: TextExtractionSettings = Field(default_factory=TextExtractionSettings)
    tables: TableExtractionSettings = Field(default_factory=TableExtractionSettings)
    equations: EquationExtractionSettings = Field(default_factory=EquationExtractionSettings)


class OutputSettings(BaseModel):
    """Settings for output."""

    directory: Path = Field(default_factory=lambda: Path.home() / "papers")


class LLMSettings(BaseModel):
    """Settings for LLM integration (v0.2)."""

    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.1
    max_tokens: int = 4096


class Settings(BaseSettings):
    """Main settings model for Papercutter."""

    model_config = SettingsConfigDict(
        env_prefix="PAPERCUTTER_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    output: OutputSettings = Field(default_factory=OutputSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # API keys (can be set via environment variables or config file)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    mathpix_app_id: str | None = None
    mathpix_app_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Settings are loaded from (in order of priority, highest first):
    1. Environment variables (PAPERCUTTER_* prefix)
    2. YAML config file (~/.papercutter/config.yaml)
    3. Default values
    """
    yaml_config = _load_yaml_config()
    return Settings(**yaml_config)
