# Papercutter

Extract structured data from academic papers into analysis-ready datasets.

Papercutter converts PDF collections into structured Markdown using [Docling](https://github.com/DS4SD/docling), then applies LLM-based extraction to produce CSV datasets and LaTeX reports suitable for systematic reviews and meta-analyses.

## Installation

```bash
pip install papercutter[full]
```

Requires Python 3.10+ and an OpenAI or Anthropic API key.

Optional extras:
```bash
pip install papercutter[docling]  # PDF processing only
pip install papercutter[llm]      # LLM extraction only
pip install papercutter[report]   # Report generation only
```

## Usage

### 1. Ingest

Convert PDFs to Markdown and extract tables.

```bash
papercutter ingest ./pdfs/
```

Output: `markdown/`, `tables/`, `figures/`, `inventory.json`

### 2. Configure

Generate an extraction schema from paper abstracts.

```bash
papercutter configure
```

Output: `columns.yaml`

```yaml
columns:
  - key: sample_size
    description: "Total observations (N)"
    type: integer
  - key: method
    description: "Estimation strategy (DiD, RDD, OLS, etc.)"
    type: string
  - key: effect
    description: "Main treatment coefficient"
    type: float
```

### 3. Grind

Extract data from all papers.

```bash
papercutter grind
```

Output: `extractions.json`

### 4. Report

Generate analysis outputs.

```bash
papercutter report            # matrix.csv + review.pdf
papercutter report --condensed  # appendix format
```

## Book Pipeline

Process books or handbooks with chapter-level extraction.

```bash
papercutter book index ./book.pdf   # Detect chapters
papercutter book extract            # Extract text
papercutter book grind              # Summarize chapters
papercutter book report             # Generate PDF
```

Output: `output/book_summary.pdf`

## Output Files

| File | Description |
|------|-------------|
| `inventory.json` | Processing status for each PDF |
| `columns.yaml` | Extraction schema definition |
| `extractions.json` | Extracted data per paper |
| `matrix.csv` | Flattened dataset for R/Stata/Python |
| `review.pdf` | LaTeX report with structured summaries |

## License

MIT
