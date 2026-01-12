# Papercutter

Turn your PDF collection into a dataset you can actually use.

For researchers doing systematic reviews, meta-analyses, or literature surveys who have PDFs piling up but need structured data for analysis.

Requires Python 3.10+ and an OpenAI or Anthropic API key.

## Installation

```bash
pip install papercutter[full]
```

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

### 3. Extract

Extract data from all papers using LLM.

```bash
papercutter extract
```

Output: `extractions.json`

### 4. Report

Generate analysis outputs.

```bash
papercutter report            # matrix.csv + review.pdf
papercutter report --condensed  # appendix format
```

## Book Pipeline

Process books or handbooks with chapter-level summaries.

```bash
papercutter book index ./book.pdf   # Detect chapters
papercutter book extract            # Extract text
papercutter book summarize          # Summarize chapters
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

## Examples

See real pipeline outputs in [`examples/`](examples/):

- **book-ab-testing/** - Output from processing "Trustworthy Online Controlled Experiments" (Kohavi, Tang & Xu, 2020). Includes chapter detection (23 chapters) and LLM-generated summaries.

## Documentation

Full documentation: [papercutter.readthedocs.io](https://papercutter.readthedocs.io)

## License

MIT
