# Papercutter Factory

### Automated Evidence Synthesis Pipeline for Research

**Papercutter Factory** is a local, batch-processing pipeline designed to transform unstructured academic PDF collections into structured datasets and systematic review reports.

It addresses the specific tooling gap between reference managers (Zotero, Mendeley) and analysis software (R, Stata). Unlike generic "Chat with PDF" tools, Papercutter is architected for **extraction reliability, reproducibility, and scale**. It utilizes **Docling** to convert PDFs into structured Markdown and JSON before applying LLM-based extraction, ensuring tabular data and complex layouts are preserved.

---

## Key Capabilities

*   **Pipeline Architecture:** A stateless, resumable workflow. Processing status is tracked per file, allowing large batches to be paused and resumed without data loss.
*   **High-Fidelity Digitization:** Utilizes IBM's **Docling** to convert PDFs into structured Markdown, preserving table geometry and section hierarchy better than standard text extraction.
*   **Schema Validation:** Test extraction schemas on samples with source quotes for every extracted data point to verify accuracy.
*   **Book Summarization:** Process entire books or handbooks with chapter detection, extraction, and synthesis into formatted PDF reports.

---

## Installation

```bash
pip install papercutter[full]
```

**System Requirements:**
*   Python 3.10 or higher
*   **API Access:** Requires `OPENAI_API_KEY` environment variable (or Anthropic API key)
*   **For PDF Reports:** LaTeX installation (MacTeX, TeX Live, or MiKTeX)

**Modular Installation:**
```bash
pip install papercutter           # Core only
pip install papercutter[docling]  # PDF processing
pip install papercutter[llm]      # LLM extraction
pip install papercutter[report]   # PDF report generation
```

---

## Workflow Overview

The system operates in four phases to ensure data integrity.

### 1. Ingest (Digitization)

Converts raw PDFs into structured Markdown and extracts tables.

```bash
papercutter ingest ./pdfs/
```

*   **Process:** Scans directory, runs Docling conversion (PDF -> Markdown + Tables)
*   **Output:** `markdown/`, `tables/`, `figures/`, `inventory.json`

### 2. Configure (Schema Definition)

Generates an extraction schema by analyzing paper abstracts.

```bash
papercutter configure
```

*   **Process:** Samples papers and uses LLM to propose extraction fields
*   **Output:** `columns.yaml`

**Example `columns.yaml`:**
```yaml
columns:
  - key: sample_size
    description: "The total number of observations (N). Exclude year ranges."
    type: integer
  - key: estimation_method
    description: "The primary statistical strategy (e.g. DiD, RDD, OLS)."
    type: string
  - key: treatment_effect
    description: "The extracted coefficient for the main treatment."
    type: float
```

### 3. Grind (Extraction)

Executes LLM-based extraction for all papers.

```bash
papercutter grind
```

*   **Process:** Extracts metadata, narrative fields, and custom schema fields
*   **Output:** `extractions.json`

### 4. Report (Synthesis)

Compiles final artifacts for analysis and reading.

```bash
papercutter report
```

*   **Outputs:**
    *   `matrix.csv`: Flattened dataset ready for R/Stata/Pandas
    *   `review.pdf`: LaTeX document with structured summaries

**Condensed Mode** (for appendix tables):
```bash
papercutter report --condensed
```

---

## Book Summarization Pipeline

Process entire books, textbooks, or handbooks with chapter-level analysis.

```bash
# 1. Detect chapters from PDF bookmarks
papercutter book index ./book.pdf

# 2. Extract chapter text
papercutter book extract

# 3. Summarize each chapter with LLM
papercutter book grind

# 4. Generate formatted PDF report
papercutter book report
```

**Output:** `output/book_summary.pdf` with one page per chapter including:
- Main thesis and unique insights
- Key evidence and counterexamples
- Key terms and definitions
- Book-level synthesis with themes and intellectual journey

---

## Project Structure

```text
my_project/
├── pdfs/                   # Raw PDF repository
├── markdown/               # Docling-converted Markdown
├── tables/                 # Extracted tables (JSON)
├── figures/                # Extracted figures
├── columns.yaml            # Extraction schema
├── inventory.json          # Processing status tracker
├── extractions.json        # Extracted data
├── matrix.csv              # Final dataset
└── review.pdf              # Compiled report
```

---

## License

MIT License. Open for academic and commercial use.
