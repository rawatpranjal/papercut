# Papercutter E2E Test Results - RIGOROUS AUDIT

**Date**: 2026-01-08
**Auditor**: Claude (Ruthless Mode)
**Verdict**: FAIL - Critical bugs found

---

## Executive Summary

| Category | Status | Critical Issues |
|----------|--------|-----------------|
| Input Validation | **FAIL** | 4 crashes on invalid input |
| Infinite Loops | **FAIL** | Confirmed infinite loop with overlap >= chunk_size |
| Data Integrity | **FAIL** | Overlap not maintained correctly |
| Test Coverage | **FAIL** | 39% coverage, CLI at 0% |
| Security | **NOT TESTED** | Path traversal vulnerabilities identified |

---

## CRITICAL BUGS CONFIRMED

### BUG-001: INFINITE LOOP (CRITICAL)
**Location**: `src/papercutter/core/text.py:82-106`
**Trigger**: `--chunk-size 100 --overlap 200`
**Status**: **CONFIRMED** - Process ran indefinitely at 75% CPU

```bash
# This command causes infinite loop:
python3 -m papercutter.cli.app extract text file.pdf --chunk-size 100 --overlap 200 --pages 1
# Had to kill process after 24+ seconds
```

### BUG-002: CRASH ON INCOMPLETE PAGE RANGE (HIGH)
**Location**: `src/papercutter/cli/extract.py:28`
**Trigger**: `--pages "1-"`

```
ValueError: invalid literal for int() with base 10: ''
```

**Stack trace shown to user** - bad UX.

### BUG-003: CRASH ON NON-NUMERIC PAGES (HIGH)
**Location**: `src/papercutter/cli/extract.py:30`
**Trigger**: `--pages "abc"`

```
ValueError: invalid literal for int() with base 10: 'abc'
```

### BUG-004: NEGATIVE PAGE INDEX CREATED (HIGH)
**Location**: `src/papercutter/cli/extract.py:30`
**Trigger**: `--pages "0"`
**Result**: Creates `page_list = [-1]` which extracts the LAST page instead of showing error.

**Silent wrong behavior** - user thinks they're getting page 0 but gets last page.

### BUG-005: DATA INTEGRITY - OVERLAP NOT MAINTAINED (MEDIUM)
**Location**: `src/papercutter/core/text.py:82-106`
**Evidence**:

```
Chunk 2 ends with: 'ata), ora computational error.'
Chunk 3 starts with: 'in instrumentation (e.g., logg'
```

Overlap of 100 chars requested but chunks don't share the expected 100 characters.

---

## TEST RESULTS BY PHASE

### Phase 1: Crash Tests

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Empty pages | `--pages ""` | Error message | No crash, silent | PASS |
| Incomplete range | `--pages "1-"` | Error message | ValueError + stack trace | **FAIL** |
| Non-numeric | `--pages "abc"` | Error message | ValueError + stack trace | **FAIL** |
| Zero page | `--pages "0"` | Error message | Silently extracts last page | **FAIL** |
| Negative chunk | `--chunk-size -100` | Error message | Not tested (file issue) | SKIP |

### Phase 2: Infinite Loop Tests

| Test | Parameters | Expected | Actual | Status |
|------|------------|----------|--------|--------|
| overlap > chunk | `--chunk-size 100 --overlap 200` | Error or valid output | **INFINITE LOOP** | **FAIL** |
| overlap == chunk | `--chunk-size 100 --overlap 100` | Error or valid output | Not tested | SKIP |

### Phase 3: Data Integrity Tests

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Chunk overlap correctness | Last 100 chars of chunk N == first 100 chars of chunk N+1 | 1 of 3 overlaps incorrect | **FAIL** |

### Phase 4: Unit Test Coverage

| Module | Coverage | Status |
|--------|----------|--------|
| Overall | 39% | **FAIL** |
| CLI (app.py, extract.py, fetch.py) | 0% | **CRITICAL** |
| PDF extraction (pdfplumber.py) | 0% | **CRITICAL** |
| Fetcher.fetch() methods | 0% | **CRITICAL** |
| core/text.py | 83% | OK |
| core/tables.py | 92% | OK |

**67 tests pass but test the WRONG THINGS** - only validation, not behavior.

---

## SECURITY ISSUES IDENTIFIED (NOT TESTED)

From code review:

1. **Path Traversal**: Author names from external APIs (arXiv, DOI) used in filenames without sanitization
2. **Weak Regex**: DOI pattern accepts `10.1234/<script>alert('xss')</script>`
3. **Silent Exception Catch**: `except Exception: pass` hides all errors
4. **No URL Encoding**: DOIs with special chars break URL construction

---

## REQUIRED FIXES

### Priority 1 (CRITICAL)
1. **Add validation for overlap < chunk_size** in `text.py` and `extract.py`
2. **Add try-catch in parse_pages()** with user-friendly error messages
3. **Validate page numbers are positive integers**

### Priority 2 (HIGH)
4. **Fix break point logic** - maintain exact overlap
5. **Add CLI tests** - 0% coverage is unacceptable
6. **Add integration tests** for actual PDF extraction

### Priority 3 (MEDIUM)
7. **Sanitize filenames** from external API data
8. **URL encode DOIs** before API calls
9. **Replace silent exception catches** with proper error handling

---

## PASS CRITERIA (NOT MET)

| Criterion | Required | Actual | Status |
|-----------|----------|--------|--------|
| Zero crashes on invalid input | 0 | 3+ | **FAIL** |
| Zero infinite loops | 0 | 1+ | **FAIL** |
| Zero data integrity issues | 0 | 1+ | **FAIL** |
| Test coverage > 70% | 70% | 39% | **FAIL** |
| All unit tests pass | 100% | 100% | PASS |

---

## RECOMMENDATION

**DO NOT SHIP** until critical bugs are fixed. The infinite loop bug alone could crash user systems. The input validation bugs expose stack traces to users. The data integrity bug produces incorrect output silently.
