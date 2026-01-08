"""Pytest fixtures for Papercutter tests."""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    """Copy sample PDF to temp directory if it exists."""
    # Look for a sample PDF in fixtures
    fixtures_dir = Path(__file__).parent / "fixtures"
    sample = fixtures_dir / "sample.pdf"

    if sample.exists():
        dst = tmp_path / "sample.pdf"
        shutil.copy(sample, dst)
        return dst

    # If no fixture, skip test
    pytest.skip("No sample PDF fixture available")


@pytest.fixture
def output_dir(tmp_path) -> Path:
    """Create a temporary output directory."""
    output = tmp_path / "output"
    output.mkdir()
    return output
