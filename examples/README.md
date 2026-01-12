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
