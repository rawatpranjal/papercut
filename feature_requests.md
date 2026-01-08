# Papercutter Feature Specifications

## Philosophy
Small, practical automations that save researchers time on tedious tasks.
NOT boiling the ocean - just quality-of-life improvements.

---

# Tier 1: Quick Wins

## 1. Auto-detect output format from extension

### Usage
```bash
papercutter extract refs paper.pdf -o refs.bib   # Auto-detects → bibtex
papercutter extract refs paper.pdf -o refs.json  # Auto-detects → json
papercutter extract refs paper.pdf -o refs.yaml  # Error: unsupported format
papercutter extract refs paper.pdf               # Default: JSON to stdout
```

### Implementation
```python
# In cli/extract.py refs() function
def infer_format(output_path: Optional[Path], explicit_format: Optional[str]) -> str:
    if explicit_format:
        return explicit_format
    if output_path:
        ext = output_path.suffix.lower()
        if ext == ".bib":
            return "bibtex"
        elif ext in (".json", ".yaml", ".yml"):
            return ext.lstrip(".")
    return "json"  # default
```

### Behavior
- `--format` flag takes precedence over extension
- Unknown extensions → error with list of supported formats
- No output file → JSON to stdout (current behavior)

---

## 2. Batch fetch from file

### Usage
```bash
# papers.txt
arxiv:1706.03762
doi:10.1038/nature12373
nber:12345
url:https://example.com/paper.pdf
# Comments start with #

papercutter fetch batch papers.txt -o ./library/
# Fetching 4 papers...
# [1/4] arxiv:1706.03762 → Vaswani_2017_attention.pdf ✓
# [2/4] doi:10.1038/nature12373 → Kucsko_2013_thermometry.pdf ✓
# [3/4] nber:12345 → Yeyati_2006_liquidity.pdf ✓
# [4/4] url:https://... → paper.pdf ✓
# Done: 4 succeeded, 0 failed

papercutter fetch batch papers.txt -o ./library/ --continue-on-error
# [1/4] arxiv:1706.03762 ✓
# [2/4] doi:INVALID → FAILED: DOI not found
# [3/4] nber:12345 ✓
# ...
# Done: 3 succeeded, 1 failed
# Failed: doi:INVALID (see errors.log)
```

### File Format
```
# One paper per line
# Format: source:identifier

arxiv:1706.03762
arxiv:2301.00001
doi:10.1038/nature12373
nber:12345
ssrn:1234567
url:https://arxiv.org/pdf/2005.14165.pdf

# Blank lines and comments ignored
```

### Options
```
--continue-on-error    Don't stop on first failure
--parallel N           Download N papers concurrently (default: 1)
--delay SECONDS        Delay between downloads (default: 0, respects rate limits)
--dry-run              Show what would be downloaded
```

### Output
```
./library/
├── Vaswani_2017_attention.pdf
├── Kucsko_2013_thermometry.pdf
├── Yeyati_2006_liquidity.pdf
└── batch_results.json  # optional: --save-results
```

---

## 3. Clean error messages

### Current (Bad)
```
╭───────────────────── Traceback (most recent call last) ──────────────────────╮
│ /Users/.../papercutter/cli/fetch.py:32 in arxiv                                 │
│ ... 50 more lines ...                                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
PaperNotFoundError: Paper not found on arXiv: 9999.99999
```

### Proposed (Good)
```bash
papercutter fetch arxiv 9999.99999
# Error: Paper not found on arXiv: 9999.99999
# Hint: Check the ID format (e.g., 2301.00001 or 1706.03762)

papercutter fetch arxiv invalid
# Error: Invalid arXiv ID format: 'invalid'
# Hint: arXiv IDs look like: 2301.00001, 1706.03762, or hep-th/9901001

papercutter extract text missing.pdf
# Error: File not found: missing.pdf

papercutter extract text corrupt.pdf
# Error: Cannot read PDF: corrupt.pdf
# Details: Not a valid PDF file
```

### Implementation
```python
# Wrap CLI commands with error handler
@app.command()
def arxiv(...):
    try:
        # existing code
    except PaperNotFoundError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.hint:
            console.print(f"[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
```

### Verbose mode
```bash
papercutter fetch arxiv bad-id --verbose
# Shows full traceback for debugging
```

---

## 4. Quiet mode

### Usage
```bash
# Normal output
papercutter fetch arxiv 1706.03762 -o ./papers
# Downloaded: papers/Vaswani_2017_attention.pdf
# Title: Attention Is All You Need

# Quiet mode - no output on success
papercutter fetch arxiv 1706.03762 -o ./papers --quiet
# (nothing printed)

# Quiet mode - still shows errors
papercutter fetch arxiv bad-id -o ./papers --quiet
# Error: Paper not found

# Super quiet - exit code only
papercutter fetch arxiv 1706.03762 -o ./papers -qq
# (nothing, check $?)
```

### Exit Codes
```
0 = success
1 = error (paper not found, network error, etc.)
2 = usage error (bad arguments)
```

### Use Case: Scripts
```bash
#!/bin/bash
for id in 1706.03762 2301.00001 1909.11942; do
    if papercutter fetch arxiv $id -o ./papers --quiet; then
        echo "Downloaded $id"
    else
        echo "Failed: $id"
    fi
done
```

---

## 5. Export Python API

### Usage
```python
from papercutter import (
    # Fetchers
    fetch_arxiv,
    fetch_doi,
    fetch_url,

    # Extractors
    extract_text,
    extract_tables,
    extract_refs,

    # Classes for advanced use
    ArxivFetcher,
    DOIFetcher,
    TextExtractor,
)

# Simple API
pdf_path = fetch_arxiv("1706.03762", output_dir="./papers")
# Returns: Path("./papers/Vaswani_2017_attention.pdf")

text = extract_text(pdf_path)
# Returns: str

text_with_meta = extract_text(pdf_path, return_dict=True)
# Returns: {"text": "...", "word_count": 8234, "pages": 15}

chunks = extract_text(pdf_path, chunk_size=1000, overlap=200)
# Returns: List[str]

tables = extract_tables(pdf_path)
# Returns: List[Table]

refs = extract_refs(pdf_path)
# Returns: List[Reference]

# Advanced API
fetcher = ArxivFetcher()
doc = fetcher.fetch("1706.03762", output_dir="./papers")
# doc.path, doc.title, doc.authors, doc.abstract
```

### Module Structure
```python
# papercutter/__init__.py
from papercutter.api import (
    fetch_arxiv,
    fetch_doi,
    fetch_url,
    extract_text,
    extract_tables,
    extract_refs,
)

from papercutter.fetchers import ArxivFetcher, DOIFetcher, SSRNFetcher
from papercutter.core import TextExtractor, TableExtractor, ReferenceExtractor

__all__ = [
    "fetch_arxiv", "fetch_doi", "fetch_url",
    "extract_text", "extract_tables", "extract_refs",
    "ArxivFetcher", "DOIFetcher", "SSRNFetcher",
    "TextExtractor", "TableExtractor", "ReferenceExtractor",
]
```

---

# Tier 2: High-Value Features

## 6. Paper metadata sidecar files

### Usage
```bash
papercutter fetch arxiv 1706.03762 -o ./papers --metadata
# Downloaded: papers/Vaswani_2017_attention.pdf
# Metadata:   papers/Vaswani_2017_attention.meta.json
```

### Metadata File Content
```json
{
  "source": "arxiv",
  "id": "1706.03762",
  "title": "Attention Is All You Need",
  "authors": [
    {"name": "Ashish Vaswani", "affiliation": "Google Brain"},
    {"name": "Noam Shazeer", "affiliation": "Google Brain"}
  ],
  "abstract": "The dominant sequence transduction models...",
  "published": "2017-06-12",
  "updated": "2017-12-06",
  "categories": ["cs.CL", "cs.LG"],
  "doi": "10.48550/arXiv.1706.03762",
  "pdf_url": "https://arxiv.org/pdf/1706.03762",
  "comment": "15 pages, 5 figures",
  "fetched_at": "2026-01-08T14:30:00Z",
  "file": "Vaswani_2017_attention.pdf"
}
```

### Options
```bash
--metadata          Save metadata alongside PDF
--metadata-only     Fetch metadata without PDF
--metadata-format   json (default) | yaml | bibtex
```

---

## 7. Follow references

### Usage
```bash
# Extract and try to fetch all cited papers
papercutter refs follow paper.pdf -o ./cited_papers/
# Found 42 references
# Resolved 28 to downloadable sources:
#   - 15 arXiv
#   - 8 DOI
#   - 5 URL
# Downloading...
# [1/28] Ba et al. 2016 → arxiv:1607.06450 ✓
# [2/28] Bahdanau et al. 2014 → arxiv:1409.0473 ✓
# ...
# Done: 25 downloaded, 3 failed, 14 unresolved

# Limit depth
papercutter refs follow paper.pdf --depth 1 -o ./cited/
# Only direct citations (depth 1)

papercutter refs follow paper.pdf --depth 2 -o ./cited/
# Citations of citations too

# Dry run
papercutter refs follow paper.pdf --dry-run
# Shows what would be downloaded
```

### Resolution Strategy
```
1. Look for arXiv ID in reference (arxiv:XXXX.XXXXX)
2. Look for DOI (10.XXXX/...)
3. Look for URL
4. Try to search arXiv/Semantic Scholar by title+author
5. Mark as unresolved if none work
```

### Output
```
./cited_papers/
├── Ba_2016_layer_normalization.pdf
├── Bahdanau_2014_attention.pdf
├── ...
├── _unresolved.txt  # List of refs that couldn't be fetched
└── _manifest.json   # Full resolution details
```

---

## 8. Search before fetch

### Usage
```bash
papercutter search arxiv "transformer attention mechanism"
#  #  ID            Title                                      Authors        Year
#  1  1706.03762    Attention Is All You Need                  Vaswani et al  2017
#  2  1810.04805    BERT: Pre-training of Deep Bidirectional   Devlin et al   2018
#  3  2005.14165    Language Models are Few-Shot Learners      Brown et al    2020
#  ...
#
# Fetch with: papercutter fetch arxiv <ID>

papercutter search arxiv "transformer" --author "Vaswani" --limit 5 --year 2017

papercutter search arxiv "transformer" --json
# Returns JSON array for scripting
```

### Interactive Mode
```bash
papercutter search arxiv "transformer" --interactive
#  1. Attention Is All You Need (1706.03762)
#  2. BERT (1810.04805)
#  3. GPT-3 (2005.14165)
#
# Enter numbers to download (e.g., 1,3 or 1-3): 1,3
# Downloading 2 papers...
```

### Sources
```bash
papercutter search arxiv "..."      # arXiv
papercutter search semantic "..."   # Semantic Scholar
papercutter search crossref "..."   # CrossRef (DOI)
```

---

## 9. Abstract extraction

### Usage
```bash
papercutter extract abstract paper.pdf
# Returns just the abstract text (plain text to stdout)

papercutter extract abstract paper.pdf --json
{
  "abstract": "The dominant sequence transduction models...",
  "word_count": 156
}

papercutter extract abstract paper.pdf -o abstract.txt
# Saves to file
```

### Detection Strategy
```
1. Look for "Abstract" heading
2. Extract text until next section (Introduction, 1., etc.)
3. Handle variations: "ABSTRACT", "Summary", "Overview"
4. For arXiv papers: prefer metadata abstract over PDF extraction
```

---

## 10. BibTeX key auto-generation

### Current (Bad)
```bibtex
@misc{2016,
  author = {[1] JimmyLeiBa and JamieRyanKiros...},
  year = {2016},
}
```

### Proposed (Good)
```bibtex
@article{ba2016layer,
  author = {Ba, Jimmy Lei and Kiros, Jamie Ryan and Hinton, Geoffrey E.},
  title = {Layer Normalization},
  year = {2016},
  journal = {arXiv preprint arXiv:1607.06450},
  url = {https://arxiv.org/abs/1607.06450},
}
```

### Key Generation Rules
```
{first_author_lastname}{year}{first_title_word}
Examples:
- vaswani2017attention
- ba2016layer
- devlin2018bert
- brown2020language

Collision handling:
- vaswani2017attention
- vaswani2017improving  (different paper same author/year)
```

### Author Parsing Fix
```
Input:  "JimmyLeiBa,JamieRyanKiros,andGeoffreyEHinton"
Output: ["Ba, Jimmy Lei", "Kiros, Jamie Ryan", "Hinton, Geoffrey E."]

Strategy:
1. Split on common delimiters (, and ; &)
2. Detect CamelCase boundaries
3. Infer first/last name order
4. Handle "and" as separator
```

---

# Tier 3: Power User Features

## 11. Paper similarity/dedup

### Usage
```bash
papercutter library dedup ./papers/
# Scanning 127 PDFs...
# Found 4 potential duplicate groups:
#
# Group 1 (same paper, different filenames):
#   - attention_is_all_you_need.pdf
#   - Vaswani_2017_attention.pdf
#   - 1706.03762.pdf
#   Action: Keep Vaswani_2017_attention.pdf? [y/n/skip]
#
# Group 2 (different versions):
#   - BERT_v1.pdf (2018-10-11)
#   - BERT_v2.pdf (2019-05-24)
#   Action: Keep latest? [y/n/skip]
```

### Detection Methods
```
1. Exact hash match (SHA256 of content)
2. Title similarity (>95% Levenshtein)
3. First page similarity (for different versions)
4. arXiv ID match in different filenames
```

---

## 13. Citation graph

### Usage
```bash
papercutter refs graph paper.pdf -o citations.json
```

### Output Format
```json
{
  "root": {
    "id": "1706.03762",
    "title": "Attention Is All You Need",
    "authors": ["Vaswani et al."]
  },
  "nodes": [
    {"id": "ref_1", "title": "Layer Normalization", "resolved": "arxiv:1607.06450"},
    {"id": "ref_2", "title": "Neural Machine Translation", "resolved": "arxiv:1409.0473"}
  ],
  "edges": [
    {"from": "root", "to": "ref_1"},
    {"from": "root", "to": "ref_2"}
  ]
}
```

### Visualization
```bash
papercutter refs graph paper.pdf --format dot -o citations.dot
# Then: dot -Tpng citations.dot -o citations.png
```

---

## 14. LLM-ready chunking with metadata

### Usage
```bash
papercutter extract text paper.pdf --chunk-size 1000 --include-metadata
```

### Output
```json
{
  "chunks": [
    {
      "id": 0,
      "text": "Abstract\nThe dominant sequence...",
      "metadata": {
        "page": 1,
        "section": "Abstract",
        "char_start": 0,
        "char_end": 987,
        "figures_referenced": [],
        "tables_referenced": []
      }
    },
    {
      "id": 1,
      "text": "1 Introduction\nRecurrent neural networks...",
      "metadata": {
        "page": 1,
        "section": "1 Introduction",
        "char_start": 988,
        "char_end": 1956,
        "figures_referenced": [],
        "tables_referenced": []
      }
    }
  ]
}
```

---

## 15. Section extraction

### Usage
```bash
papercutter extract section paper.pdf --section "Related Work"
# Returns text of that section

papercutter extract section paper.pdf --list
# 1. Abstract
# 2. Introduction
# 3. Background
# 4. Model Architecture
# 5. Training
# 6. Results
# 7. Related Work
# 8. Conclusion
# 9. References
```

---

## 18. Merge bibliographies

### Usage
```bash
papercutter refs merge refs1.bib refs2.bib refs3.bib -o combined.bib
# Merged 45 + 32 + 18 = 87 references (8 duplicates removed)
# Output: combined.bib (79 unique entries)
```

### Dedup Strategy
```
1. Match by DOI (exact)
2. Match by arXiv ID (exact)
3. Match by title + year (fuzzy)
```

---

## 19. Convert formats

### Usage
```bash
papercutter refs convert refs.bib --to json -o refs.json
papercutter refs convert refs.json --to bibtex -o refs.bib
papercutter refs convert refs.bib --to yaml -o refs.yaml
papercutter refs convert refs.bib --to csv -o refs.csv
```

---

## 20. Reading time estimate

### Usage
```bash
papercutter info paper.pdf
# File: Vaswani_2017_attention.pdf
# Pages: 15
# Words: 8,234
# Figures: 5
# Tables: 3
# References: 42
# Est. reading time: 35 min (at 250 wpm)
#
# Sections:
#   Abstract (156 words)
#   Introduction (892 words)
#   ...

papercutter info paper.pdf --json
# Returns structured data
```

---

# Implementation Priority

## Phase 1: Foundation (Week 1)
1. Clean error messages (#3) - Critical for UX
2. Export Python API (#5) - Enables everything else
3. Quiet mode (#4) - Quick win

## Phase 2: Usability (Week 2)
4. Auto-detect format (#1) - Quick win
5. BibTeX key fix (#10) - Fixes broken feature
6. Reading time estimate (#20) - Easy, high visibility

## Phase 3: Productivity (Week 3-4)
7. Batch fetch (#2) - High value
8. Metadata sidecars (#6) - Enables library building
9. Search before fetch (#8) - Common workflow

## Phase 4: Advanced (Future)
10. Follow references (#7)
11. Section extraction (#15)
12. LLM chunking with metadata (#14)
13. Everything else

---

# Anti-Goals (Don't Build)

- Full-text search engine (use Elasticsearch)
- PDF editing/annotation (use PDF tools)
- Reference manager UI (use Zotero/Mendeley)
- OCR for scanned PDFs (use dedicated tools)
- Translation (use DeepL/Google)
- Summarization (use LLMs directly)
