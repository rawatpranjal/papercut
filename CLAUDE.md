# CLAUDE.md - Papercutter Factory

## Overview

**Papercutter Factory** is a CLI pipeline for automated evidence synthesis in systematic literature reviews. It transforms unstructured PDF collections into structured datasets and reports.

**Entry point**: `papercutter` CLI (or `python -m papercutter`)

## Project Structure

```
src/papercutter/
├── cli/                    # Typer CLI commands
│   ├── app.py              # Main CLI app
│   ├── init_cmd.py         # papercutter init
│   ├── ingest_cmd.py       # papercutter ingest
│   ├── configure_cmd.py    # papercutter configure
│   ├── grind_cmd.py        # papercutter grind
│   ├── factory_report_cmd.py  # papercutter report
│   ├── status_cmd.py       # papercutter status
│   └── utils.py            # Shared CLI utilities
├── ingest/                 # PDF processing pipeline
│   ├── pipeline.py         # Main IngestPipeline orchestrator
│   ├── splitter.py         # Sawmill - splits large PDFs into chapters
│   ├── matcher.py          # BibTeX matching logic
│   ├── docling_wrapper.py  # Docling PDF-to-Markdown conversion
│   ├── ocr_fallback.py     # Fallback when Docling fails
│   └── fetchers/           # Paper downloading (arXiv, DOI, etc.)
├── grinding/               # LLM-based extraction
│   ├── extractor.py        # Evidence extraction via LLM
│   ├── schema.py           # ExtractionSchema definition
│   ├── generator.py        # Auto-generate schemas from papers
│   ├── matrix.py           # ExtractionMatrix results storage
│   └── synthesis.py        # Summary generation
├── project/                # Project state management
│   ├── manager.py          # ProjectManager lifecycle
│   ├── inventory.py        # ProjectInventory tracking
│   └── state.py            # Config models (YAML-based)
├── reporting/              # Output generation
│   └── builder.py          # ReportBuilder (LaTeX/Markdown)
├── llm/                    # LLM integration
│   ├── client.py           # LiteLLM wrapper (multi-provider)
│   ├── prompts.py          # Prompt templates
│   └── schemas.py          # Response schemas
├── config/                 # Configuration
│   └── settings.py         # Pydantic settings
├── extractors/             # PDF extraction (for OCR fallback)
│   └── pdfplumber.py       # PdfPlumber implementation
├── output/                 # Output formatting
│   └── formatter.py        # JSON/pretty formatting
├── utils/                  # Shared utilities
├── legacy/                 # Old v1.x code (preserved, not active)
├── __init__.py
├── __main__.py
├── api.py
└── exceptions.py
```

## CLI Commands

```bash
# Initialize a new project
papercutter init my_project

# Process PDFs (split, match BibTeX, convert to Markdown)
papercutter ingest ./pdfs/ --bib references.bib

# Define extraction schema
papercutter configure

# Extract evidence (pilot or full)
papercutter grind --pilot
papercutter grind --full

# Generate report
papercutter report

# Check project status
papercutter status
```

## Development Workflow

```bash
# Install in development mode
pip install -e ".[dev]"

# Install with Docling (PDF processing)
pip install -e ".[docling]"

# Install with Factory features
pip install -e ".[factory]"

# Install all
pip install -e ".[dev,docling,factory,llm]"
```

### Using the Makefile

```bash
make install-dev   # Install with dev dependencies
make test          # Run tests
make lint          # Run ruff linter
make typecheck     # Run mypy
make check         # Run lint + typecheck + test
```

## Pipeline Architecture

### 1. Ingest Phase
- `IngestPipeline` scans directories for PDFs
- `Splitter` (Sawmill) detects and splits large volumes (500+ pages)
- `BibTeXMatcher` links PDFs to citations via fuzzy title matching
- `DoclingWrapper` converts PDFs to structured Markdown
- `OCRFallback` uses PdfPlumber when Docling fails

### 2. Configure Phase
- `SchemaGenerator` analyzes paper abstracts
- Proposes extraction schema via LLM
- User refines `config.yaml` with typed columns

### 3. Grind Phase
- `Extractor` processes papers through LLM
- Pilot mode: random sample with source quotes for validation
- Full mode: process all papers idempotently
- `ExtractionMatrix` stores results

### 4. Report Phase
- `ReportBuilder` generates LaTeX or Markdown
- Outputs: `matrix.csv` (data) + `systematic_review.pdf` (document)

## Configuration

Project config: `config.yaml` in project root
Global config: `~/.papercutter/config.yaml`

Environment variables:
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

## Testing

```bash
pytest tests/
pytest --cov=src/papercutter tests/
```

## Dependencies

**Core**: typer, pdfplumber, pypdf, httpx, pydantic, pyyaml, rich

**Optional**:
- `docling` - IBM's PDF-to-Markdown converter
- `litellm` - Multi-provider LLM support
- `jinja2` - Report templating

## Code Style

- **Line length**: 100 characters
- **Linter**: Ruff (E, W, F, I, B, UP, RUF rules)
- **Type checking**: mypy with Python 3.10 target

## File Locations Reference

| Purpose | Location |
|---------|----------|
| Main CLI app | `src/papercutter/cli/app.py` |
| Ingest pipeline | `src/papercutter/ingest/pipeline.py` |
| Evidence extractor | `src/papercutter/grinding/extractor.py` |
| Project manager | `src/papercutter/project/manager.py` |
| Report builder | `src/papercutter/reporting/builder.py` |
| LLM client | `src/papercutter/llm/client.py` |
| Settings | `src/papercutter/config/settings.py` |
| Exceptions | `src/papercutter/exceptions.py` |
