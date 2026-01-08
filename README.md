# Papercutter

[![PyPI version](https://badge.fury.io/py/papercutter.svg)](https://pypi.org/project/papercutter/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/rawatpranjal/papercutter/actions/workflows/ci.yml/badge.svg)](https://github.com/rawatpranjal/papercutter/actions/workflows/ci.yml)

Extract knowledge from academic papers. A CLI-first Python package for researchers.

## Installation

```bash
pip install papercutter
```

With LLM features (summarization, reports, study aids):
```bash
pip install papercutter[llm]
```

With fast PDF processing (PyMuPDF):
```bash
pip install papercutter[fast]
```

All optional dependencies:
```bash
pip install papercutter[all]
```

### Development Installation

```bash
git clone https://github.com/rawatpranjal/papercutter.git
cd papercutter
pip install -e ".[dev]"
```

## Quick Start

### Fetch Papers

Download papers from various academic sources:

```bash
# From arXiv
papercutter fetch arxiv 2301.00001

# From DOI
papercutter fetch doi 10.1257/aer.20180779

# From SSRN
papercutter fetch ssrn 4123456

# From NBER
papercutter fetch nber w29000

# From direct URL
papercutter fetch url "https://example.com/paper.pdf" --name smith_2024
```

### Extract Text

Extract clean text from PDFs:

```bash
# Full text to stdout
papercutter extract text paper.pdf

# Save to file
papercutter extract text paper.pdf --output paper.txt

# Chunk for LLM processing
papercutter extract text paper.pdf --chunk-size 4000 --overlap 200

# Extract specific pages
papercutter extract text paper.pdf --pages "1-10,15"
```

### Extract Tables

Extract tables from PDFs as CSV or JSON:

```bash
# All tables to stdout as JSON
papercutter extract tables paper.pdf

# Save as CSV files
papercutter extract tables paper.pdf --output ./tables/ --format csv

# Extract from specific pages
papercutter extract tables paper.pdf --pages "5-10" --format json
```

### Extract References

Extract bibliography as BibTeX:

```bash
# BibTeX to stdout
papercutter extract refs paper.pdf

# Save to file
papercutter extract refs paper.pdf --output refs.bib

# As JSON
papercutter extract refs paper.pdf --format json
```

## Configuration

Papercutter stores configuration in `~/.papercutter/config.yaml`:

```yaml
output:
  directory: ~/papers

extraction:
  backend: pdfplumber
  text:
    chunk_size: null
    chunk_overlap: 200
  tables:
    format: csv

# LLM settings (v0.2)
llm:
  default_provider: anthropic
  default_model: claude-sonnet-4-20250514
```

Environment variables override config:
```bash
export PAPERCUTTER_ANTHROPIC_API_KEY=sk-ant-...
export PAPERCUTTER_OPENAI_API_KEY=sk-...
```

## Migration from Papercut

Papercutter is a direct rename of the original Papercut project. To upgrade an existing installation:

1. Reinstall the package: `pip uninstall papercut && pip install papercutter`.
2. Update scripts and shell aliases to call `papercutter` instead of `papercut`.
3. Rename your config directory if you have custom settings: `mv ~/.papercut ~/.papercutter`.
4. (Optional) Rename the cache directory to retain cached artifacts: `mv ~/.cache/papercut ~/.cache/papercutter`.
5. Update any `PAPERCUT_*` environment variables to the new `PAPERCUTTER_*` prefix.

## Development

Run tests:
```bash
pytest tests/
```

Run linting:
```bash
ruff check src/
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.
