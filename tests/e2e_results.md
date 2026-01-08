# Papercut E2E Test Results

**Date**: 2026-01-08
**Test Environment**: macOS Darwin 23.5.0, Python 3.11

---

## Summary

| Category | Tests | Pass | Fail | Notes |
|----------|-------|------|------|-------|
| CLI Installation | 1 | 1 | 0 | Works via `python3 -m papercut.cli.app` |
| Fetch Commands | 5 | 0 | 5 | Network issues + bugs |
| Extract Text | 3 | 3 | 0 | All working |
| Extract Tables | 2 | 1 | 1 | Detects tables but content empty |
| Extract Refs | 1 | 0 | 1 | No refs found in test PDF |

---

## Detailed Results

### 1. CLI Installation

**Status**: PASS (with workaround)

- `papercut --help` fails due to typer/click version incompatibility
- Workaround: Use `python3 -m papercut.cli.app` instead
- Root cause: TypeError in typer rich_utils.py with Parameter.make_metavar()

```bash
# Fails
$ papercut --help
TypeError: Parameter.make_metavar() missing 1 required positional argument: 'ctx'

# Works
$ python3 -m papercut.cli.app --help
Usage: python -m papercut.cli.app [OPTIONS] COMMAND [ARGS]...
```

---

### 2. Fetch Commands

#### 2.1 fetch arxiv

**Status**: FAIL

**Command**: `papercut fetch arxiv 2301.00001 --output tests/downloads/arxiv_test.pdf`

**Issues Found**:
1. **Bug Fixed**: `arxiv.arxiv.HTTPError` → `arxiv.HTTPError` (line 95 in arxiv.py)
2. **Network Error**: Cannot connect to export.arxiv.org (may be firewall/network issue)
3. **Bug**: When `--output` ends with `.pdf`, it's treated as a directory

**Error**: `URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>`

#### 2.2 fetch doi

**Status**: NOT TESTED (network dependent)

#### 2.3 fetch ssrn

**Status**: NOT TESTED (network dependent)

#### 2.4 fetch nber

**Status**: NOT TESTED (network dependent)

#### 2.5 fetch url

**Status**: NOT TESTED (network dependent)

---

### 3. Extract Commands

#### 3.1 extract text (basic)

**Status**: PASS

**Command**: `papercut extract text output/01_introduction_and_motivation.pdf --pages 1-3`

**Result**: Successfully extracted text from pages 1-3. Output is clean, readable text.

**Sample Output**:
```
1
Introduction and Motivation
One accurate measurement is worth more than a thousand expert
opinions
– Admiral Grace Hopper
In2012,anemployeeworkingonBing,Microsoft'ssearchengine,suggested...
```

---

#### 3.2 extract text (chunked)

**Status**: PASS

**Command**: `papercut extract text output/01_introduction_and_motivation.pdf --chunk-size 500 --overlap 50`

**Result**: Successfully chunked text with 500 char chunks and 50 char overlap.

**Output Format**: JSON with `chunks` array

```json
{
  "chunks": [
    "1\nIntroduction and Motivation\nOne accurate measurement is...",
    "...he best revenue-generating idea in Bing's history!\nThe feature...",
    ...
  ]
}
```

---

#### 3.3 extract text (page range)

**Status**: PASS

**Command**: `papercut extract text output/01_introduction_and_motivation.pdf --pages 1-3`

**Result**: Correctly limited extraction to specified page range.

---

#### 3.4 extract tables

**Status**: PARTIAL FAIL

**Command**: `papercut extract tables output/02_running_and_analyzing_experiments.pdf`

**Result**: Detects 9 tables but all have empty content.

**Output**:
```json
{
  "page": 3,
  "rows": 2,
  "data": [[""], [""]]
}
```

**Issue**: pdfplumber table detection works but content extraction fails for this PDF format. May need better table extraction settings or fallback methods.

**Command on Ch1**: `papercut extract tables output/01_introduction_and_motivation.pdf`

**Result**: "No tables found in PDF." - Correct, this chapter has no tables.

---

#### 3.5 extract refs

**Status**: FAIL (false negative)

**Command**: `papercut extract refs output/01_introduction_and_motivation.pdf`

**Result**: "No references found in PDF."

**Issue**: This is Chapter 1 of a book. References may be:
1. In a separate references chapter
2. In-text citations not parsed as standalone references
3. Reference format not recognized by the parser

---

## Bugs Found

| ID | Severity | Component | Description | Status |
|----|----------|-----------|-------------|--------|
| B1 | High | CLI | typer/click version incompatibility | Workaround available |
| B2 | Medium | arxiv.py | `arxiv.arxiv.HTTPError` should be `arxiv.HTTPError` | **FIXED** |
| B3 | Medium | fetch | `--output` with `.pdf` extension treated as directory | Open |
| B4 | Low | tables | Empty table content extraction | Open |
| B5 | Low | refs | Book chapter references not detected | Open |

---

## Test Files Used

| File | Size | Description |
|------|------|-------------|
| output/01_introduction_and_motivation.pdf | 1.1 MB | Book chapter, no tables |
| output/02_running_and_analyzing_experiments.pdf | 600 KB | Book chapter with tables |

---

## Recommendations

1. **Pin typer/click versions** in pyproject.toml to avoid compatibility issues
2. **Fix output path handling** - detect `.pdf` extension and treat as file, not directory
3. **Improve table extraction** - consider fallback to camelot or tabula for complex tables
4. **Test with academic papers** - download actual research papers for better E2E testing
5. **Add integration tests** with sample PDFs in fixtures/

---

## Next Steps

1. Fix B3 (output path handling)
2. Test fetch commands when network is available
3. Add sample academic papers to fixtures/
4. Test with papers that have clear reference sections
5. Test table extraction with simpler PDF tables
