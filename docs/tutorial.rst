Tutorial
========

This tutorial walks through papercutter's two main pipelines with examples.

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

   papercutter extract

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

   papercutter book index ./platform-economics.pdf

This detects chapters from PDF bookmarks or text patterns:

.. code-block:: text

   Found 4 chapters:
    1. What Makes a Platform (pp. 1-45)
    2. Network Effects and Critical Mass (pp. 46-98)
    3. Pricing Multi-Sided Markets (pp. 99-156)
    4. Platform Competition (pp. 157-210)

   Saved to: book_inventory.json

**Step 2: Extract chapter text**

Extract the text from each chapter:

.. code-block:: bash

   papercutter book extract

Creates ``chapters/`` directory with one file per chapter.

**Step 3: Summarize chapters**

Run LLM summarization on each chapter:

.. code-block:: bash

   papercutter book summarize

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


Sample Output: Platform Economics
---------------------------------

Illustrative output from processing a platform economics textbook.

Book Synthesis
^^^^^^^^^^^^^^

.. code-block:: json

   {
     "book_thesis": "Multi-sided platforms create value by reducing transaction costs between distinct user groups who could not efficiently find each other otherwise. Success requires solving the chicken-and-egg problem through strategic subsidization and achieving critical mass before network effects can sustain growth.",
     "key_themes": [
       "Network Effects and Critical Mass",
       "Multi-Sided Pricing Strategy",
       "Platform Competition Dynamics"
     ],
     "intellectual_journey": "The book establishes what distinguishes platforms from traditional businesses (Chapter 1), then analyzes the network effects that make them valuable but difficult to launch (Chapter 2). It develops pricing frameworks for multi-sided markets (Chapter 3) before examining competitive dynamics and winner-take-all outcomes (Chapter 4).",
     "one_paragraph_summary": "Platform businesses differ fundamentally from traditional firms because they create value by facilitating interactions rather than producing goods. The central challenge is the chicken-and-egg problem: users on each side only join if the other side is already present. Successful platforms solve this through subsidization strategies, pricing one side below cost to attract them first. Once critical mass is achieved, network effects create powerful competitive moats, often leading to winner-take-all market structures."
   }

Chapter 1: What Makes a Platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "chapter_num": 1,
     "main_thesis": "Platforms are fundamentally different from traditional businesses because they create value by facilitating exchanges between two or more interdependent groups rather than by producing and selling products directly.",
     "unique_insight": "The chapter introduces the concept of 'matchmakers' as businesses whose primary function is reducing search and transaction costs between groups who benefit from finding each other.",
     "how_to": "Identify whether your business model involves facilitating interactions between distinct user groups. Map out which groups need each other and what frictions prevent them from transacting directly. Design the platform to reduce these specific frictions.",
     "key_evidence": "Credit card networks connect cardholders with merchants. Shopping malls connect shoppers with retailers. Dating apps connect people seeking relationships. In each case, neither side would show up without the other.",
     "counterexample": "This is NOT about any business with multiple customer segments. A grocery store has suppliers and customers but is not a platform—it buys goods, takes ownership, and resells them. Platforms facilitate direct interactions without taking ownership.",
     "golden_quote": "The platform does not produce the value; it enables others to produce and exchange value with each other.",
     "key_terms": [
       "Multi-sided platform",
       "Transaction costs",
       "Matchmaker",
       "Indirect network effects",
       "Platform participants"
     ]
   }

Chapter 2: Network Effects
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

   {
     "chapter_num": 2,
     "main_thesis": "Platforms exhibit indirect network effects where value to users on one side increases with the number of users on the other side. This creates the chicken-and-egg problem: neither side joins without the other, making platform launches extremely difficult.",
     "unique_insight": "The chapter distinguishes between same-side effects (users valuing other users on their own side, which can be positive or negative) and cross-side effects (users valuing participants on the other side). Most platforms have positive cross-side effects but may have negative same-side effects due to competition.",
     "how_to": "Map the network effects structure of your platform. Identify which side is more price-sensitive and which side generates more cross-side value. Launch by subsidizing the more price-sensitive side to achieve critical mass, then monetize the side that values access to the now-large user base.",
     "key_evidence": "Video game consoles subsidize hardware (sold at or below cost) to attract gamers, then charge game developers for access to the installed base. Nightclubs let women in free to attract men who pay cover charges. Search engines provide free search to users and charge advertisers for access.",
     "counterexample": "This is NOT about traditional economies of scale where unit costs fall with volume. Network effects are demand-side: the product becomes more valuable to each user as more users join, regardless of production costs.",
     "golden_quote": "Getting the first users is the hardest part. After critical mass, the platform can grow on its own momentum.",
     "key_terms": [
       "Indirect network effects",
       "Chicken-and-egg problem",
       "Critical mass",
       "Same-side effects",
       "Cross-side effects"
     ]
   }


Real Example Outputs
--------------------

See real outputs from processing "Trustworthy Online Controlled Experiments" (Kohavi, Tang & Xu):

`examples/book-ab-testing on GitHub <https://github.com/rawatpranjal/papercutter/tree/main/examples/book-ab-testing>`_

Includes:

- ``book_inventory.json`` - Chapter detection (23 chapters)
- ``book_extractions.json`` - LLM summaries with thesis, insights, evidence, key terms
