# Papercut

Extract knowledge from academic papers. A CLI-first Python package for researchers.

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

For LLM features (v0.2):
```bash
pip install -e ".[llm]"
```

## Quick Start

### Fetch Papers

Download papers from various academic sources:

```bash
# From arXiv
papercut fetch arxiv 2301.00001

# From DOI
papercut fetch doi 10.1257/aer.20180779

# From SSRN
papercut fetch ssrn 4123456

# From NBER
papercut fetch nber w29000

# From direct URL
papercut fetch url "https://example.com/paper.pdf" --name smith_2024
```

### Extract Text

Extract clean text from PDFs:

```bash
# Full text to stdout
papercut extract text paper.pdf

# Save to file
papercut extract text paper.pdf --output paper.txt

# Chunk for LLM processing
papercut extract text paper.pdf --chunk-size 4000 --overlap 200

# Extract specific pages
papercut extract text paper.pdf --pages "1-10,15"
```

### Extract Tables

Extract tables from PDFs as CSV or JSON:

```bash
# All tables to stdout as JSON
papercut extract tables paper.pdf

# Save as CSV files
papercut extract tables paper.pdf --output ./tables/ --format csv

# Extract from specific pages
papercut extract tables paper.pdf --pages "5-10" --format json
```

### Extract References

Extract bibliography as BibTeX:

```bash
# BibTeX to stdout
papercut extract refs paper.pdf

# Save to file
papercut extract refs paper.pdf --output refs.bib

# As JSON
papercut extract refs paper.pdf --format json
```

## Configuration

Papercut stores configuration in `~/.papercut/config.yaml`:

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
export PAPERCUT_ANTHROPIC_API_KEY=sk-ant-...
export PAPERCUT_OPENAI_API_KEY=sk-...
```

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
