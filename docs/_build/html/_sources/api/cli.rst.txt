CLI
===

.. code-block:: bash

   papercutter [COMMAND] [OPTIONS]

Fetch Commands
--------------

Download papers from various sources.

.. code-block:: bash

   papercutter fetch arxiv 2301.00001
   papercutter fetch doi 10.1257/aer.20180779
   papercutter fetch ssrn 3550274
   papercutter fetch nber w29000
   papercutter fetch url https://example.com/paper.pdf

Extract Commands
----------------

Extract content from PDFs.

.. code-block:: bash

   papercutter extract text paper.pdf [-p PAGES] [--chunk-size N]
   papercutter extract tables paper.pdf [-f csv|json]
   papercutter extract refs paper.pdf [-f bibtex|json]

Index Commands
--------------

Build and inspect document structure.

.. code-block:: bash

   papercutter index paper.pdf [--type paper|book] [--force]
   papercutter chapters book.pdf
   papercutter info paper.pdf

Read Command
------------

Extract text by section or chapter.

.. code-block:: bash

   papercutter read paper.pdf --pages 10-14
   papercutter read paper.pdf --section "Methods"
   papercutter read book.pdf --chapter 5
   papercutter read paper.pdf --all

Cache Commands
--------------

Manage extraction cache.

.. code-block:: bash

   papercutter cache-info paper.pdf
   papercutter clear-cache [paper.pdf]

LLM Commands
------------

AI-powered analysis (requires ``pip install papercutter[llm]``).

summarize
^^^^^^^^^

Generate AI summaries of papers.

.. code-block:: bash

   papercutter summarize paper.pdf [OPTIONS]

Options:

- ``--focus``: Focus area for the summary

  - ``methods``: Focus on methodology and approach
  - ``results``: Focus on findings and outcomes
  - ``contributions``: Focus on novel contributions

- ``--length``: Summary length

  - ``short``: Brief overview
  - ``default``: Standard length
  - ``long``: Detailed summary

- ``--pages``: Page range to summarize (e.g., ``1-10,15``)
- ``--model``: LLM model to use (e.g., ``claude-sonnet-4-20250514``)
- ``--json``: Output as JSON

report
^^^^^^

Generate structured reports for different audiences.

.. code-block:: bash

   papercutter report paper.pdf [OPTIONS]

Options:

- ``--template``: Built-in template name

  - ``reading-group``: Discussion-focused summary for reading groups
  - ``referee``: Critical peer review style report
  - ``meta``: Notes for meta-analysis synthesis
  - ``executive``: Business/policy executive summary

- ``--custom-template``: Path to custom template file
- ``--pages``: Page range to analyze
- ``--model``: LLM model to use
- ``--json``: Output as JSON

study
^^^^^

Generate study materials from books.

.. code-block:: bash

   papercutter study book.pdf [OPTIONS]

Options:

- ``--mode``: Type of study material to generate

  - ``summary``: Chapter summary (default)
  - ``concepts``: Key concepts extraction
  - ``quiz``: Practice quiz questions
  - ``flashcards``: Spaced repetition flashcards

- ``--chapter``: Chapter number to process
- ``--pages``: Page range (alternative to chapter)
- ``--model``: LLM model to use
- ``--json``: Output as JSON
