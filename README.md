# Papercutter Factory

### Automated Evidence Synthesis Pipeline for Research

**Papercutter Factory** is a local, batch-processing pipeline designed to transform unstructured academic PDF collections into structured datasets and systematic review reports.

It addresses the specific tooling gap between reference managers (Zotero, Mendeley) and analysis software (R, Stata). Unlike generic "Chat with PDF" tools, Papercutter is architected for **extraction reliability, reproducibility, and scale**. It utilizes **Docling** to convert PDFs into structured Markdown and JSON before applying LLM-based extraction, ensuring tabular data and complex layouts are preserved.

---

## Key Capabilities

*   **Pipeline Architecture:** A stateless, resumable workflow. Processing status is tracked per file, allowing large batches to be paused and resumed without data loss.
*   **High-Fidelity Digitization:** Utilizes IBM's **Docling** to convert PDFs into structured Markdown, preserving table geometry and section hierarchy better than standard text extraction.
*   **Intelligent Splitting:** Automatically detects large volumes (e.g., handbooks, dissertations) and splits them into chapter-level units for granular analysis.
*   **Schema Validation (Pilot Mode):** Includes a "Pilot Protocol" to test extraction schemas on a random sample. Includes source quotes for every extracted data point to verify accuracy before processing the full library.
*   **Bibliographic Linking:** Fuzzy-matches PDF contents to existing BibTeX records to ensure metadata consistency.

---

## Installation

Papercutter is a comprehensive toolkit that relies on PyTorch and Docling for document layout analysis. A standard installation requires Python 3.10+.

```bash
pip install papercutter
```

**System Requirements:**
*   **Hardware:** A GPU is recommended for optimal OCR and layout analysis speed, though the system functions on CPU.
*   **API Access:** Requires an active API key for OpenAI (`export OPENAI_API_KEY=...`) or Anthropic.
*   **Optional:** Tesseract OCR (for legacy scanned documents).

---

## Workflow Overview

The system operates in four distinct phases to ensure data integrity.

### 1. Ingest (Digitization)
Initializes the project structure and converts raw PDFs into a unified internal format.

```bash
# Initialize a new review project
papercutter init my_project

# Process PDFs and link to metadata
cd my_project
papercutter ingest ./raw_pdfs/ --bib references.bib
```

*   **Process:** Scans directories, identifies duplicates via SHA256, splits large volumes, and runs Docling conversion.
*   **Metadata:** If a BibTeX file is provided, PDFs are linked to citations via fuzzy title matching.

### 2. Configure (Schema Definition)
Defines the variables to be extracted from the literature.

```bash
papercutter configure
```

*   **Process:** The system analyzes abstracts from the ingested library and proposes a draft schema. The user generates a `config.yaml` file to enforce strict types on extracted data.

**Example `config.yaml`:**
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

### 3. Grind (Extraction Loop)
Executes the LLM-based extraction and summarization.

```bash
# Step A: Pilot Run (Validation)
papercutter grind --pilot
```
*   Processes a random 5-paper sample.
*   Generates a **Traceability Report** (`pilot_matrix.csv`) containing the extracted value alongside the *exact quote* from the text used to derive it. This allows researchers to audit LLM performance.

```bash
# Step B: Full Execution
papercutter grind --full
```
*   Processes the remaining library. This step is idempotent; already processed papers are skipped.

### 4. Report (Synthesis)
Compiles final artifacts for analysis and reading.

```bash
papercutter report
```

*   **Outputs:**
    *   `matrix.csv`: A flattened dataset of all extracted variables, ready for import into R/Stata/Pandas.
    *   `systematic_review.pdf`: A compiled LaTeX document containing:
        *   **Structured Summaries:** One-page standardized syntheses of every paper.
        *   **Contribution Grid:** A consolidated appendix layout for rapid comparison.

---

## Project Structure

Papercutter enforces a standardized directory structure to manage state.

```text
my_project/
├── input/                  # Raw PDF repository
├── config.yaml             # Extraction schema definition
├── .papercutter/           # Internal state (Markdown cache, Inventory)
└── output/
    ├── matrix.csv          # Final dataset for analysis
    ├── systematic_review.pdf
    └── pilot_trace.csv     # Audit trail for verification
```

---

## Common Use Cases

**Meta-Regression Analysis**
> *Goal:* Extract specific regression coefficients and standard errors from 50+ empirical papers.
> *Workflow:* Define `coefficient`, `standard_error`, and `model_specification` in the schema. Use the Pilot Mode to ensure the LLM distinguishes between "Main Results" and "Robustness Checks."

**Large Volume Processing**
> *Goal:* Analyze a Handbook or multi-chapter Report.
> *Workflow:* The Ingest phase detects the volume size. The Splitter module separates chapters into individual units. The Report phase generates a "Flashcard" style appendix for rapid review.

**Library Remediation**
> *Goal:* Organize a messy folder of PDFs with inconsistent filenames.
> *Workflow:* The Ingest phase uses header analysis to identify papers and links them to a clean BibTeX file, generating a structured inventory of the collection.

---

## License

MIT License. Open for academic and commercial use.
