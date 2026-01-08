# Papercut: End-to-End Test Suite

These tests should be run against real papers, not mocks. A test passes only if a human reviewer confirms the output is useful and accurate.

---

## Test Category 1: Paper Type Diversity

### Test 1.1: Classic Empirical Paper (Difference-in-Differences)
**Input**: Card & Krueger (1994) "Minimum Wages and Employment"
**Template**: `reading_group`
**Pass Criteria**:
- [ ] Correctly identifies DiD as identification strategy
- [ ] Extracts treatment (NJ min wage hike) and control (PA)
- [ ] Finds main effect size (0.59 FTEs) and SE (0.33)
- [ ] Lists parallel trends as key assumption
- [ ] Does NOT hallucinate results not in paper

---

### Test 1.2: Instrumental Variables Paper
**Input**: Angrist & Krueger (1991) "Does Compulsory Schooling Affect Earnings?"
**Template**: `reading_group`
**Pass Criteria**:
- [ ] Identifies IV/2SLS as methodology
- [ ] Extracts instrument (quarter of birth)
- [ ] Explains the exclusion restriction logic
- [ ] Finds first-stage F-statistic if reported
- [ ] Notes weak instrument concerns if discussed

---

### Test 1.3: Regression Discontinuity Paper
**Input**: Lee (2008) "Randomized Experiments from Non-random Selection"
**Template**: `reading_group`
**Pass Criteria**:
- [ ] Identifies RDD as methodology
- [ ] Extracts running variable (vote share)
- [ ] Extracts cutoff (50%)
- [ ] Mentions bandwidth selection method
- [ ] Lists manipulation testing as robustness check

---

### Test 1.4: Pure Theory Paper (No Empirics)
**Input**: Milgrom & Weber (1982) "A Theory of Auctions and Competitive Bidding"
**Template**: `reading_group`
**Pass Criteria**:
- [ ] Does NOT try to extract "effect sizes" or "sample size"
- [ ] Identifies key theoretical contributions (revenue equivalence, linkage principle)
- [ ] Extracts main assumptions (IPV, risk neutrality, etc.)
- [ ] Summarizes key propositions/theorems
- [ ] Handles math-heavy content without garbling

---

### Test 1.5: Structural Estimation Paper
**Input**: Berry, Levinsohn, Pakes (1995) "Automobile Prices in Market Equilibrium"
**Template**: `reading_group`
**Pass Criteria**:
- [ ] Identifies structural demand estimation
- [ ] Explains the endogeneity problem and solution (BLP instruments)
- [ ] Extracts model primitives (utility specification, market definition)
- [ ] Notes computational method (contraction mapping)
- [ ] Distinguishes structural parameters from reduced-form estimates

---

### Test 1.6: Machine Learning Paper
**Input**: Athey & Imbens (2016) "Recursive Partitioning for Heterogeneous Causal Effects"
**Template**: `reading_group`
**Pass Criteria**:
- [ ] Identifies causal forests/honest trees methodology
- [ ] Explains the "honesty" concept (sample splitting)
- [ ] Extracts key hyperparameters and tuning approach
- [ ] Notes what makes this different from standard ML (causal inference focus)
- [ ] Does not confuse prediction accuracy with causal identification

---

### Test 1.7: Meta-Analysis Paper
**Input**: Chetty et al. (2011) "Adjustment Costs, Firm Responses, and Micro vs. Macro Labor Supply Elasticities"
**Template**: `meta_analysis`
**Pass Criteria**:
- [ ] Recognizes this is a synthesis paper
- [ ] Extracts the range of elasticities discussed
- [ ] Distinguishes micro vs macro estimates
- [ ] Identifies sources of heterogeneity across studies
- [ ] Does not treat synthesized estimates as original findings

---

## Test Category 2: PDF Quality & Format

### Test 2.1: Two-Column Academic Format
**Input**: Any AER/QJE paper with two-column layout
**Pass Criteria**:
- [ ] Text extraction maintains reading order (not column-interleaved)
- [ ] Footnotes are not mixed into body text
- [ ] Tables span columns correctly
- [ ] Equations are not garbled

---

### Test 2.2: Scanned PDF (OCR Required)
**Input**: Paper from 1980s, scanned from physical journal
**Pass Criteria**:
- [ ] OCR activates automatically
- [ ] Text is mostly readable (>90% character accuracy)
- [ ] Report acknowledges lower confidence due to scan quality
- [ ] Does not silently fail or return empty results

---

### Test 2.3: Working Paper with Line Numbers
**Input**: NBER working paper with line numbers in margins
**Pass Criteria**:
- [ ] Line numbers are stripped from extracted text
- [ ] Text flows naturally without "42 The coefficient..."
- [ ] Section headers are correctly identified

---

### Test 2.4: Paper with Extensive Appendix
**Input**: Paper with 15-page main text + 40-page online appendix
**Pass Criteria**:
- [ ] Main results come from main text, not appendix
- [ ] Appendix robustness checks are noted but not over-weighted
- [ ] Report distinguishes "main specification" from "appendix table A7"

---

### Test 2.5: Non-English Paper
**Input**: Paper in Spanish/French/German from European economic journal
**Pass Criteria**:
- [ ] Detects language automatically
- [ ] Either: Extracts in original language with note
- [ ] Or: Offers to translate (with disclaimer)
- [ ] Does NOT produce garbled output

---

### Test 2.6: Paper with Heavy Mathematical Notation
**Input**: Econometrica paper with 50+ equations
**Pass Criteria**:
- [ ] Equations are rendered readably (LaTeX or Unicode)
- [ ] Variable definitions are extracted
- [ ] Key equations (e.g., main estimand) are highlighted
- [ ] Report doesn't skip the math entirely

---

### Test 2.7: Corrupted/Malformed PDF
**Input**: PDF with encoding issues, missing fonts, or structural problems
**Pass Criteria**:
- [ ] Does NOT crash
- [ ] Returns partial results with clear error message
- [ ] Indicates which sections could not be parsed
- [ ] Suggests user try alternative (e.g., re-download, use different source)

---

## Test Category 3: Book Processing

### Test 3.1: Graduate Textbook
**Input**: Wooldridge "Econometric Analysis of Cross Section and Panel Data" (800+ pages)
**Template**: `book`
**Pass Criteria**:
- [ ] Correctly identifies chapter boundaries
- [ ] Generates chapter-level summaries
- [ ] Hierarchical output (book → part → chapter → section)
- [ ] Key theorems/results extracted per chapter
- [ ] Does not timeout or run out of memory

---

### Test 3.2: Edited Volume (Multiple Authors)
**Input**: Handbook of Econometrics chapter
**Pass Criteria**:
- [ ] Identifies it as handbook chapter, not standalone paper
- [ ] Attributes to correct author(s)
- [ ] Handles survey/review style (many citations, broad coverage)
- [ ] Extracts key themes, not just one "main finding"

---

### Test 3.3: Monograph (Book-Length Single Argument)
**Input**: Piketty "Capital in the 21st Century"
**Template**: `book`
**Pass Criteria**:
- [ ] Captures the overarching thesis
- [ ] Chapter summaries are coherent standalone
- [ ] Tracks how argument builds across chapters
- [ ] Handles mix of theory, history, and empirics

---

### Test 3.4: Technical Manual
**Input**: Stata Manual or R package vignette (PDF)
**Pass Criteria**:
- [ ] Recognizes this is documentation, not research
- [ ] Extracts function signatures/syntax
- [ ] Summarizes key options/parameters
- [ ] Does not try to find "research question" or "effect size"

---

## Test Category 4: Template & Output Formats

### Test 4.1: Reading Group Template Completeness
**Input**: Any well-structured empirical paper
**Template**: `reading_group`
**Pass Criteria**:
- [ ] All expected sections present (summary, method, data, results, assumptions, limitations)
- [ ] No section is empty
- [ ] Length is appropriate (~1 page)
- [ ] A PhD student can prep for seminar using only this output

---

### Test 4.2: Meta-Analysis Template Precision
**Input**: 10 minimum wage papers
**Template**: `meta_analysis`
**Pass Criteria**:
- [ ] All 10 papers produce valid JSON
- [ ] Effect sizes are numeric, not strings
- [ ] Standard errors are present when reported in paper
- [ ] Missing values are `null`, not hallucinated
- [ ] Output can be directly loaded into R/Python for analysis

---

### Test 4.3: LaTeX Output Compiles
**Input**: Any paper
**Format**: LaTeX
**Pass Criteria**:
- [ ] Output compiles with `pdflatex` without errors
- [ ] Special characters are escaped correctly
- [ ] Math mode is used appropriately
- [ ] Tables are valid LaTeX (booktabs style)
- [ ] References are formatted consistently

---

### Test 4.4: HTML Output Renders
**Input**: Any paper
**Format**: HTML
**Pass Criteria**:
- [ ] Valid HTML5
- [ ] Renders correctly in Chrome/Firefox/Safari
- [ ] Sections are properly nested (`<h1>`, `<h2>`, etc.)
- [ ] Code blocks (if any) are syntax highlighted
- [ ] No broken Unicode characters

---

### Test 4.5: PDF Output Quality
**Input**: Any paper
**Format**: PDF
**Pass Criteria**:
- [ ] PDF is valid and opens in standard readers
- [ ] Fonts are embedded
- [ ] Page breaks are sensible (not mid-sentence)
- [ ] Headers/footers if specified
- [ ] Looks professional enough to share

---

### Test 4.6: Custom Template Execution
**Input**: Any paper + user-defined YAML template
**Template**:
```yaml
sections:
  - methodology.identification
  - custom: "How would this apply to gig economy workers?"
  - results.main_finding
```
**Pass Criteria**:
- [ ] Custom prompt is executed
- [ ] Response is grounded in paper content
- [ ] Standard sections still extracted correctly
- [ ] Template syntax errors produce helpful error messages

---

## Test Category 5: Simulation Code Generation

### Test 5.1: Simple Theoretical Model
**Input**: Paper with 2-player Bertrand competition model
**Command**: `papercut simulate paper.pdf --language python`
**Pass Criteria**:
- [ ] Generates runnable Python code
- [ ] Model primitives (costs, demand) are parameterized
- [ ] Equilibrium computation is implemented
- [ ] Code runs without errors (may need user to fill parameters)
- [ ] Comments reference paper sections

---

### Test 5.2: Dynamic Programming Model
**Input**: Rust (1987) bus engine replacement
**Command**: `papercut simulate paper.pdf --language python`
**Pass Criteria**:
- [ ] State space defined correctly
- [ ] Bellman equation implemented
- [ ] Value function iteration or policy iteration present
- [ ] Discount factor is a parameter
- [ ] Code structure matches paper's model description

---

### Test 5.3: Agent-Based Simulation
**Input**: Paper with reinforcement learning agents in auction
**Command**: `papercut simulate paper.pdf --language python`
**Pass Criteria**:
- [ ] Agent class structure generated
- [ ] Environment/market structure captured
- [ ] Learning algorithm referenced (even if not fully implemented)
- [ ] Simulation loop is runnable

---

### Test 5.4: Statistical Replication Code
**Input**: DiD paper with clear specification
**Command**: `papercut replicate paper.pdf --language stata`
**Pass Criteria**:
- [ ] Correct regression command (`reghdfe`, `xtreg`, etc.)
- [ ] Dependent and independent variables named
- [ ] Fixed effects structure correct
- [ ] Clustering specified
- [ ] Comment noting which table/column this replicates

---

### Test 5.5: Unsimulatable Paper
**Input**: Purely empirical paper with no model
**Command**: `papercut simulate paper.pdf`
**Pass Criteria**:
- [ ] Does NOT hallucinate a model
- [ ] Returns helpful message: "No simulatable model found"
- [ ] Offers alternative: "Try `papercut replicate` for regression code"

---

## Test Category 6: Accuracy & Hallucination

### Test 6.1: Effect Size Verification
**Input**: Paper with clearly stated main result
**Test**: Compare extracted effect size to actual paper
**Pass Criteria**:
- [ ] Effect size matches paper exactly (or within rounding)
- [ ] Units are correct
- [ ] Standard error/CI matches
- [ ] Not confused with robustness check or subgroup

---

### Test 6.2: Null Result Handling
**Input**: Paper where main effect is not statistically significant
**Pass Criteria**:
- [ ] Reports the null result accurately
- [ ] Does NOT overstate findings ("effect was small" not "no effect")
- [ ] Includes p-value or CI showing insignificance
- [ ] Does not hallucinate significance

---

### Test 6.3: Missing Information Handling
**Input**: Paper that doesn't report standard errors
**Pass Criteria**:
- [ ] `standard_error` field is `null`, not invented
- [ ] Report notes: "SE not reported in paper"
- [ ] Does NOT estimate SE from other information unless asked

---

### Test 6.4: Contradictory Results Handling
**Input**: Paper where different specifications give different signs
**Pass Criteria**:
- [ ] Notes the heterogeneity in results
- [ ] Identifies which is the "preferred" specification (if stated)
- [ ] Does not cherry-pick one result

---

### Test 6.5: Fabrication Detection
**Test**: Ask for information that is NOT in the paper
**Query**: `papercut ask paper.pdf "What is the author's Twitter handle?"`
**Pass Criteria**:
- [ ] Returns "Not found in paper" or similar
- [ ] Does NOT make up a Twitter handle
- [ ] Does NOT search outside the paper

---

### Test 6.6: Citation Grounding
**Input**: Any paper, template with `_sources` enabled
**Pass Criteria**:
- [ ] Every extracted fact has a page/section reference
- [ ] References are accurate (spot-check 5 claims)
- [ ] User can verify by going to cited page

---

## Test Category 7: Batch Processing & Scale

### Test 7.1: 50-Paper Batch
**Input**: Folder with 50 PDFs
**Command**: `papercut report ./papers/*.pdf --template meta_analysis --output results.jsonl`
**Pass Criteria**:
- [ ] Completes without crashing
- [ ] All 50 papers produce output (or explicit error)
- [ ] Progress indicator shown
- [ ] Partial results saved if interrupted
- [ ] Total time < 30 minutes

---

### Test 7.2: Resume After Failure
**Input**: Start batch of 50, kill process at paper 25
**Test**: Restart same command
**Pass Criteria**:
- [ ] Resumes from paper 26, not paper 1
- [ ] Already-processed papers not re-processed
- [ ] Final output includes all 50

---

### Test 7.3: Mixed Quality Batch
**Input**: 50 papers, 5 of which are corrupted/problematic
**Pass Criteria**:
- [ ] 45 good papers processed successfully
- [ ] 5 bad papers produce clear error entries
- [ ] Errors don't stop the batch
- [ ] Summary at end: "45 succeeded, 5 failed"

---

### Test 7.4: Deduplication
**Input**: Folder with same paper twice (working paper + published version)
**Pass Criteria**:
- [ ] Detects duplicate
- [ ] Warns user: "paper_wp.pdf and paper_published.pdf appear to be same paper"
- [ ] Option to process both or skip duplicate

---

## Test Category 8: Edge Cases

### Test 8.1: Very Short Paper (Research Note)
**Input**: 5-page research note
**Pass Criteria**:
- [ ] Adjusts expectations (may not have all sections)
- [ ] Does not pad output with fluff
- [ ] Still extracts what's there

---

### Test 8.2: Very Long Paper (100+ pages)
**Input**: JMP or dissertation chapter
**Pass Criteria**:
- [ ] Handles without timeout/memory issues
- [ ] Focuses on main results, not every robustness check
- [ ] Option to set scope: `--focus main_results`

---

### Test 8.3: Paper with Redacted/Blacked Out Sections
**Input**: Paper with confidential data description redacted
**Pass Criteria**:
- [ ] Notes that some content is redacted
- [ ] Extracts what's available
- [ ] Does not hallucinate redacted content

---

### Test 8.4: Preprint vs Published Version
**Input**: arXiv preprint that differs from published version
**Pass Criteria**:
- [ ] Processes what's given (doesn't fetch published version)
- [ ] Notes if it detects "working paper" status
- [ ] Does not confuse versions

---

### Test 8.5: Supplementary Materials Only
**Input**: Just the online appendix PDF (no main paper)
**Pass Criteria**:
- [ ] Recognizes it's supplementary material
- [ ] Extracts robustness results
- [ ] Does not try to find "main finding" in appendix

---

### Test 8.6: Non-Paper PDF (Slides, Poster)
**Input**: Conference slides PDF
**Pass Criteria**:
- [ ] Detects it's not a paper
- [ ] Either: adapts extraction for slide format
- [ ] Or: returns clear error "This appears to be slides, not a paper"

---

## Test Category 9: User Experience

### Test 9.1: Helpful Error Messages
**Test**: Run various invalid commands
**Commands**:
```bash
papercut report                          # Missing input
papercut report nonexistent.pdf          # File not found
papercut report paper.pdf --template xyz # Invalid template
papercut report paper.docx               # Wrong format
```
**Pass Criteria**:
- [ ] All produce helpful, specific error messages
- [ ] Suggest correct usage
- [ ] No stack traces for user errors

---

### Test 9.2: Progress Feedback
**Input**: Large book (800 pages)
**Pass Criteria**:
- [ ] Shows progress: "Processing chapter 3/15..."
- [ ] Estimates time remaining
- [ ] User knows it's working, not frozen

---

### Test 9.3: Cost Warning
**Test**: Process 100 papers (would cost ~$5 in API calls)
**Pass Criteria**:
- [ ] Warns: "This will process 100 papers (~50k tokens, estimated cost $5)"
- [ ] Asks for confirmation
- [ ] Option to skip warning: `--yes`

---

### Test 9.4: Offline Graceful Degradation
**Test**: Run with no internet connection
**Pass Criteria**:
- [ ] Basic PDF text extraction still works
- [ ] LLM features fail gracefully with clear message
- [ ] Does not hang waiting for API

---

### Test 9.5: API Key Missing
**Test**: Run LLM feature without API key configured
**Pass Criteria**:
- [ ] Clear error: "API key not found. Set ANTHROPIC_API_KEY or configure in ~/.papercut/config.yaml"
- [ ] Links to setup documentation
- [ ] Non-LLM features still work

---

## Test Category 10: Comparative Reports

### Test 10.1: Two-Paper Comparison
**Input**: Card & Krueger (1994) vs Neumark & Wascher (2000)
**Command**: `papercut report ck1994.pdf nw2000.pdf --template comparison`
**Pass Criteria**:
- [ ] Side-by-side methodology comparison
- [ ] Notes different data sources
- [ ] Compares effect sizes with correct signs
- [ ] Identifies source of disagreement
- [ ] Does not take sides on "who is right"

---

### Test 10.2: Literature Matrix
**Input**: 10 papers on same topic
**Command**: `papercut report ./papers/*.pdf --template lit_matrix`
**Pass Criteria**:
- [ ] Produces table with one row per paper
- [ ] Columns: Paper, Method, Data, N, Effect, Significance
- [ ] Sortable/filterable output (CSV or structured)
- [ ] Identifies patterns across papers

---

## Scoring Rubric

For each test:

| Score | Meaning |
|-------|---------|
| **PASS** | Output is correct, useful, no errors |
| **PARTIAL** | Output mostly correct, minor issues |
| **FAIL** | Output wrong, unusable, or crashes |
| **SKIP** | Feature not implemented yet |

**MVP Bar**: 80% PASS rate on Category 1-4 tests before release.

**Production Bar**: 90% PASS rate on all tests.

---

## Test Data Repository

Need to assemble:
- 20 classic papers (diverse methods, fields)
- 5 problematic PDFs (scanned, corrupted, etc.)
- 2 books (textbook + monograph)
- 5 edge cases (short, long, non-English, etc.)

Want me to suggest specific papers for each test?
