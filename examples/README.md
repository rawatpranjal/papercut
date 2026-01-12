# Examples

Real outputs from running papercutter on actual books and papers.

## book-ab-testing/

Output from processing "Trustworthy Online Controlled Experiments" by Kohavi, Tang & Xu (2020).

| File | Description |
|------|-------------|
| `book_inventory.json` | Chapter detection output (23 chapters identified) |
| `book_extractions.json` | LLM-generated summaries for first 5 chapters |

### What the pipeline extracted

For each chapter:
- **Main thesis** - Core argument of the chapter
- **Unique insight** - Novel framework or technique introduced
- **Key evidence** - Concrete examples and data cited
- **Counterexample** - What this approach is NOT
- **Key terms** - Important concepts defined

Plus a book-level synthesis with themes and intellectual journey.

### Running this yourself

```bash
papercutter book index ./your-book.pdf
papercutter book extract
papercutter book summarize
papercutter book report
```

Output: `output/book_summary.pdf`

## papers-ml/

Output from processing 5 seminal machine learning papers from ArXiv:
- Attention Is All You Need (Transformers)
- BERT
- Adam Optimizer
- Batch Normalization
- Dropout

| File | Description |
|------|-------------|
| `inventory.json` | Processing status for each paper |
| `columns.yaml` | LLM-generated extraction schema |
| `extractions.json` | Extracted data with executive summary |
| `matrix.csv` | Analysis-ready flat dataset |

### What the pipeline extracted

For each paper:
- **Context** - Research question, approach, and headline finding
- **Core mechanism** - Key insight explained for PhD-level understanding
- **Method** - Identification strategy with mathematical details
- **Results** - Key estimates with interpretation
- **Contribution** - What's new and why it matters
- **Limitations** - Caveats and boundary conditions

Plus an executive summary synthesizing all 5 papers and thematic categorization.

### Running this yourself

```bash
mkdir my-review && cd my-review
# Add PDFs here
papercutter ingest ./
papercutter configure
papercutter extract
papercutter report
```

Output: `matrix.csv` + `review.pdf`
