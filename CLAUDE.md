# CLAUDE.md - Papercutter Project Context

## Project Overview

**Papercutter** (formerly Papercut) is a CLI-first Python package (v1.1.0) for extracting knowledge from academic papers. It provides a two-layer architecture:

- **Layer 1 (Extraction)**: Fetch papers from multiple sources, extract text, tables, figures, and references
- **Layer 2 (Intelligence)**: LLM-powered summarization, report generation, and study aids

**Entry point**: `papercutter` CLI (or `python -m papercutter`)

## Project Structure

```
src/papercutter/
├── cli/              # Typer CLI commands (app.py is main entry)
│   ├── app.py        # Main CLI app with command groups
│   ├── fetch.py      # `papercutter fetch <source>` commands
│   ├── extract.py    # `papercutter extract <type>` commands
│   ├── summarize_cmd.py, report_cmd.py, study_cmd.py  # Layer 2 commands
│   └── index_cmd.py, read_cmd.py, cache_cmd.py
├── core/             # Content extraction
│   ├── text.py       # TextExtractor with chunking for LLM
│   ├── tables.py     # TableExtractor → CSV/JSON
│   ├── figures.py    # FigureExtractor (requires PyMuPDF)
│   └── references.py # ReferenceExtractor → BibTeX/JSON
├── extractors/       # PDF backends
│   ├── base.py       # Extractor Protocol
│   └── pdfplumber.py # Main implementation
├── fetchers/         # Paper sources
│   ├── base.py       # BaseFetcher ABC
│   ├── arxiv.py, doi.py, ssrn.py, nber.py, url.py
├── intelligence/     # LLM-powered features
│   ├── summarize.py  # Paper summarization
│   ├── report.py     # Structured reports (reading-group, referee, etc.)
│   └── study.py      # Study aids (concepts, quizzes, flashcards)
├── llm/              # LLM client
│   ├── client.py     # LiteLLM wrapper (multi-provider)
│   └── prompts.py    # Prompt templates
├── cache/            # File-based caching (~/.cache/papercutter/)
├── config/           # Pydantic settings (~/.papercutter/config.yaml)
├── index/            # Document structure indexing
├── books/            # Chapter detection and splitting
├── output/           # JSON/pretty formatting (TTY-aware)
└── exceptions.py     # Error hierarchy with exit codes
```

## Development Workflow

```bash
# Install in development mode
pip install -e ".[dev]"

# Install with LLM features
pip install -e ".[llm]"

# Install all optional dependencies
pip install -e ".[all]"
```

### Using the Makefile

```bash
make install-dev   # Install with dev dependencies
make test          # Run tests
make test-cov      # Run tests with coverage
make lint          # Run ruff linter
make typecheck     # Run mypy
make check         # Run lint + typecheck + test
make build         # Build wheel and sdist
make clean         # Remove build artifacts
make publish-test  # Upload to TestPyPI
make publish       # Upload to PyPI
make docs          # Build Sphinx docs
```

### Manual Commands

```bash
pytest tests/
pytest --cov=src/papercutter tests/
ruff check src/
mypy src/
python -m build
```

## Key CLI Commands

**Layer 1 - Fetching:**
```bash
papercutter fetch arxiv 2301.00001
papercutter fetch doi 10.1257/aer.20180779
papercutter fetch ssrn 4123456
papercutter fetch nber w29000
papercutter fetch url "https://example.com/paper.pdf"
```

**Layer 1 - Extraction:**
```bash
papercutter extract text paper.pdf [--pages 1-10]
papercutter extract tables paper.pdf [--format csv|json]
papercutter extract refs paper.pdf [--format bibtex|json]
papercutter extract figures paper.pdf
papercutter index paper.pdf
papercutter chapters book.pdf
```

**Layer 2 - Intelligence (requires LLM):**
```bash
papercutter summarize paper.pdf [--focus methodology]
papercutter report paper.pdf [--template reading-group|referee|meta|executive]
papercutter study paper.pdf [--mode summary|concepts|quiz|flashcards]
```

## Architecture Patterns

### Extractor Protocol
```python
class Extractor(Protocol):
    def extract_text(self, path: Path, pages: range | None = None) -> str: ...
    def extract_tables(self, path: Path, pages: range | None = None) -> list[dict]: ...
    def get_page_count(self, path: Path) -> int: ...
```

### BaseFetcher (Strategy Pattern)
```python
class BaseFetcher(ABC):
    @abstractmethod
    def can_handle(self, identifier: str) -> bool: ...
    @abstractmethod
    def fetch(self, identifier: str, output_dir: Path) -> Document: ...
```

### Configuration
- Config file: `~/.papercutter/config.yaml`
- Environment variables: `PAPERCUTTER_ANTHROPIC_API_KEY`, `PAPERCUTTER_MODEL`, etc.
- Pydantic settings with nested models

### Text Chunking
`TextExtractor._chunk_text()` provides sentence-aware chunking:
- Default: 4000-char chunks with 200-char overlap
- Searches for sentence boundaries (`. `, `?\n`, `!\n`, `\n\n`)
- Critical for LLM context windows

### Caching
File-based at `~/.cache/papercutter/<pdf-hash>/`:
- `index.json` - Document structure
- `pages/` - Extracted text by page range
- `tables/`, `figures/` - Cached extractions

## Testing

```bash
# Test locations
tests/unit/test_text.py      # Text extraction & chunking
tests/unit/test_fetchers.py  # Paper fetchers
tests/unit/test_tables.py    # Table extraction
tests/unit/test_references.py # Reference parsing
tests/conftest.py            # Shared fixtures

# Run specific tests
pytest tests/unit/test_text.py -v
pytest --timeout=10 tests/  # Catch infinite loops
```

## Dependencies

**Core**: typer, pdfplumber, pypdf, arxiv, httpx, pydantic, rich, bibtexparser, pyyaml

**Optional**:
- `pymupdf` (fast) - Faster PDF processing, figure extraction
- `litellm` (llm) - Multi-provider LLM support

## Known Issues

From `tests/e2e_results.md`:
- **CRITICAL**: Infinite loop when `overlap >= chunk_size`
- **HIGH**: Input validation crashes on invalid page ranges
- **MEDIUM**: Chunk overlap not maintained correctly
- **SECURITY**: Path traversal vulnerabilities in filename handling

## Areas for Improvement

### High Priority
1. **Dependency Injection** - `Summarizer`, `ReportGenerator`, `StudyAid` create their own `PdfPlumberExtractor()`. Should accept extractor as constructor parameter for testability.

2. **Fetcher Registry** - CLI uses manual if/elif to select fetchers (`cli/fetch.py`). Implement registry/factory pattern.

3. **CLI Test Coverage** - Currently 0% for CLI modules. Add tests using Typer's `CliRunner`.

4. **Fix Chunking Edge Cases** - Validate `chunk_size > overlap` to prevent infinite loops.

### Medium Priority
5. **Cache Freshness** - Cache doesn't validate if PDF was modified. Add timestamp/hash validation.

6. **Reference Parser** - Regex-based parsing is fragile. Consider using a proper bibliography parser or ML-based approach.

7. **Configurable Truncation** - `intelligence/summarize.py:77-79` has hard-coded 100,000 char limit. Make configurable.

8. **Document Type Detection** - `indexer.py:211-237` uses basic heuristics (50+ pages = book). Improve detection logic.

### Low Priority
9. **Prompt Templates** - Move from `llm/prompts.py` to external files for easier customization.

10. **Cache Eviction** - No policy for clearing old cache entries. Implement LRU or size-based eviction.

11. **PDF Edge Cases** - Handle encrypted PDFs, scanned (image-only) PDFs gracefully.

12. **Error Handling** - Some broad exception catches in `indexer.py` that silently fail.

## Code Style

- **Line length**: 100 characters
- **Linter**: Ruff (E, W, F, I, B, UP, RUF rules)
- **Type checking**: mypy with Python 3.10 target
- **Imports**: isort with `papercutter` as first-party

## File Locations Reference

| Purpose | Location |
|---------|----------|
| Main CLI app | `src/papercutter/cli/app.py` |
| Settings | `src/papercutter/config/settings.py` |
| LLM client | `src/papercutter/llm/client.py` |
| Prompts | `src/papercutter/llm/prompts.py` |
| Exceptions | `src/papercutter/exceptions.py` |
| Text chunking | `src/papercutter/core/text.py` |
| Document indexing | `src/papercutter/index/indexer.py` |
| Cache store | `src/papercutter/cache/store.py` |
