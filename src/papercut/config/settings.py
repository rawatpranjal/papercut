"""Pydantic settings for Papercut configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_config_dir() -> Path:
    """Get the configuration directory, creating it if needed."""
    config_dir = Path.home() / ".papercut"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_config_dir() / "config.yaml"


class TextExtractionSettings(BaseModel):
    """Settings for text extraction."""

    chunk_size: Optional[int] = None
    chunk_overlap: int = 200


class TableExtractionSettings(BaseModel):
    """Settings for table extraction."""

    format: str = "csv"


class ExtractionSettings(BaseModel):
    """Settings for content extraction."""

    backend: str = "pdfplumber"
    text: TextExtractionSettings = Field(default_factory=TextExtractionSettings)
    tables: TableExtractionSettings = Field(default_factory=TableExtractionSettings)


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
    """Main settings model for Papercut."""

    model_config = SettingsConfigDict(
        env_prefix="PAPERCUT_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    output: OutputSettings = Field(default_factory=OutputSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # API keys (can be set via environment variables)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
