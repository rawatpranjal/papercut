Tutorial
========

This tutorial walks through papercutter's two main pipelines with real examples.

Paper Collection Pipeline
-------------------------

For processing collections of academic papers (systematic reviews, meta-analyses, literature surveys),
use the main pipeline. This extracts structured data from multiple PDFs into a flat dataset.

**Step 1: Ingest PDFs**

Place your papers in a directory and convert them to markdown:

.. code-block:: bash

   mkdir my-review && cd my-review
   # Copy PDFs here
   papercutter ingest ./

This creates:

.. code-block:: text

   markdown/
     paper1.md
     paper2.md
     ...
   tables/
     paper1.json     # Extracted tables
     paper2.json
   figures/
     paper1/         # Extracted figures
     paper2/
   inventory.json    # Processing status

**Step 2: Configure extraction schema**

Generate a schema based on your papers:

.. code-block:: bash

   papercutter configure

The LLM samples your papers and proposes extraction fields. Edit ``columns.yaml`` to customize:

.. code-block:: yaml

   columns:
     - key: sample_size
       description: "Total observations (N)"
       type: integer
     - key: method
       description: "Estimation method (OLS, DiD, RDD, IV)"
       type: string
     - key: effect_size
       description: "Main treatment coefficient"
       type: float
     - key: standard_error
       description: "SE of main coefficient"
       type: float

**Step 3: Extract data**

Run LLM extraction on all papers:

.. code-block:: bash

   papercutter grind

For each paper, the LLM extracts:

- **Metadata** - Title, authors, year, paper type
- **Narrative fields** - Context, method, results, key findings
- **Custom fields** - Values from your ``columns.yaml`` schema

Output is saved to ``extractions.json``.

**Step 4: Generate outputs**

Create the final reports:

.. code-block:: bash

   papercutter report

This generates:

- ``matrix.csv`` - Flat dataset for R/Stata/Pandas analysis
- ``review.pdf`` - Evidence dossier with one-page summaries

For a condensed appendix view:

.. code-block:: bash

   papercutter report --condensed


Book Summarization
------------------

For processing entire books (textbooks, handbooks, monographs), use the ``book`` subcommand.
This pipeline detects chapters, extracts text, summarizes each chapter with an LLM, and generates
a formatted PDF report.

**Step 1: Index the book**

Point papercutter at your PDF:

.. code-block:: bash

   papercutter book index ./trustworthy-experiments.pdf

This detects chapters from PDF bookmarks or text patterns:

.. code-block:: text

   Found 5 chapters:
    1. Introduction and Motivation (pp. 21-43)
    2. Running and Analyzing Experiments (pp. 44-56)
    3. Twyman's Law and Experimentation Trustworthiness (pp. 57-75)
    4. Experimentation Platform and Culture (pp. 76-98)
    5. Speed Matters (pp. 99-107)

   Saved to: book_inventory.json

**Step 2: Extract chapter text**

Extract the text from each chapter:

.. code-block:: bash

   papercutter book extract

Creates ``chapters/`` directory with one file per chapter.

**Step 3: Summarize chapters**

Run LLM extraction on each chapter:

.. code-block:: bash

   papercutter book grind

For each chapter, the LLM extracts:

- **Main thesis** - The core argument
- **Unique insight** - Novel framework or technique introduced
- **How to** - Practical steps to implement the approach
- **Key evidence** - Concrete examples and data
- **Counterexample** - What this approach is NOT
- **Key terms** - New concepts introduced

It also synthesizes a book-level overview with themes and intellectual journey.

**Step 4: Generate PDF report**

Create the final report:

.. code-block:: bash

   papercutter book report

Generates ``output/book_summary.pdf`` with title page, TOC, and one page per chapter.


Sample Outputs
--------------

Real outputs from processing "Trustworthy Online Controlled Experiments" by Kohavi, Tang & Xu.

Book Synthesis
^^^^^^^^^^^^^^

.. code-block:: json

   {
     "book_thesis": "This book argues that trustworthy online controlled experiments (A/B tests) are the essential, systematic methodology for making valid, data-driven decisions in digital product development.",
     "key_themes": [
       "Trustworthy Causal Inference",
       "Systematic Experimentation Culture",
       "Quantifying Business Value"
     ],
     "intellectual_journey": "The book begins by establishing the foundational principles and necessity of controlled experiments (Chapter 1), then details the process for designing and running valid tests (Chapter 2). It builds by introducing critical laws for detecting errors and ensuring trustworthiness (Chapter 3), before scaling up to discuss platform infrastructure and organizational maturity (Chapter 4), and concludes with an advanced application for quantifying performance impact (Chapter 5).",
     "one_paragraph_summary": "Trustworthy Online Controlled Experiments presents a comprehensive guide to implementing rigorous A/B testing as the core methodology for data-driven decision-making in digital products. It establishes that most ideas fail to improve key metrics, making systematic experimentation essential. The book details the entire process from foundational concepts like the Overall Evaluation Criterion (OEC) and experiment design, to critical diagnostics like Sample Ratio Mismatch checks governed by Twyman's Law, to scaling an experimentation platform and culture through a defined maturity model."
   }

Chapter Summary (Chapter 1)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "chapter_num": 1,
     "main_thesis": "Online controlled experiments (A/B tests) are the gold standard for establishing causality in digital product development, providing unparalleled ability to make trustworthy, data-driven decisions. Organizations are poor at assessing the value of ideas, and controlled experiments reveal that most ideas fail to improve key metrics.",
     "unique_insight": "The chapter introduces the Overall Evaluation Criterion (OEC) as a quantitative measure that must be measurable in the short term yet believed to causally drive long-term strategic objectives. It also presents the 'three tenets' framework for organizations.",
     "how_to": "Implement experimentation platforms to run thousands of controlled experiments annually. Define clear OECs that balance multiple objectives. Randomize properly using users as randomization units. Accept that most ideas will fail while pursuing incremental improvements.",
     "key_evidence": "Bing's ad headline experiment (2012) increased revenue by 12% ($100M annually in US alone). Amazon's 'People who searched for X bought Y' algorithm increased overall revenue by 3%. Microsoft data shows only one-third of ideas improve intended metrics, while Bing/Google success rates are 10-20%.",
     "counterexample": "This is NOT correlation-based inference—the chapter warns against assuming causality from observational data, as demonstrated by Microsoft Office 365 where users seeing error messages had lower churn rates but showing more errors would not reduce churn.",
     "golden_quote": "Online controlled experiments are: The best scientific way to establish causality with high probability.",
     "key_terms": [
       "Overall Evaluation Criterion (OEC)",
       "Randomization Unit",
       "Variant",
       "Parameter",
       "Hierarchy of Evidence"
     ]
   }

Chapter Summary (Chapter 3)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "chapter_num": 3,
     "main_thesis": "Twyman's Law—that any figure that looks interesting or different is usually wrong—is the most important law in data analysis for experimentation. Extreme or surprising results are more likely to be caused by errors than by genuine effects.",
     "unique_insight": "This chapter introduces Sample Ratio Mismatch (SRM) as a critical diagnostic tool. SRM occurs when the actual ratio of users between variants deviates from the designed ratio, indicating underlying problems like browser redirects, lossy instrumentation, or bad hash functions.",
     "how_to": "Implement SRM checks with warnings for ratios outside 0.99-1.01 for equally sized variants. Hide reports when p-values are below 0.001. Avoid redirect implementations, use server-side mechanisms instead. Plot usage over time to detect novelty/primacy effects.",
     "key_evidence": "The MSN portal experiment showed a 3.3% increase in user engagement after correcting for SRM caused by bot filtering. 50% of US traffic on Bing comes from bots (over 90% in China and Russia). GoodUI.org's evaluation of 115 A/B tests found most were underpowered.",
     "counterexample": "This is NOT about celebrating surprising positive results—the chapter warns against building stories around unusually good outcomes without rigorous validation.",
     "golden_quote": "Good data scientists are skeptics: they look at anomalies, they question results, and they invoke Twyman's law when the results look too good.",
     "key_terms": [
       "Twyman's Law",
       "Sample Ratio Mismatch (SRM)",
       "Stable Unit Treatment Value Assumption (SUTVA)",
       "Heterogeneous Treatment Effects",
       "Simpson's Paradox"
     ]
   }
