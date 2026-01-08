CLI
===

.. code-block:: bash

   papercut [COMMAND] [OPTIONS]

Fetch Commands
--------------

Download papers from various sources.

.. code-block:: bash

   papercut fetch arxiv 2301.00001
   papercut fetch doi 10.1257/aer.20180779
   papercut fetch ssrn 3550274
   papercut fetch nber w29000
   papercut fetch url https://example.com/paper.pdf

Extract Commands
----------------

Extract content from PDFs.

.. code-block:: bash

   papercut extract text paper.pdf [-p PAGES] [--chunk-size N]
   papercut extract tables paper.pdf [-f csv|json]
   papercut extract refs paper.pdf [-f bibtex|json]

Index Commands
--------------

Build and inspect document structure.

.. code-block:: bash

   papercut index paper.pdf [--type paper|book] [--force]
   papercut chapters book.pdf
   papercut info paper.pdf

Read Command
------------

Extract text by section or chapter.

.. code-block:: bash

   papercut read paper.pdf --pages 10-14
   papercut read paper.pdf --section "Methods"
   papercut read book.pdf --chapter 5
   papercut read paper.pdf --all

Cache Commands
--------------

Manage extraction cache.

.. code-block:: bash

   papercut cache-info paper.pdf
   papercut clear-cache [paper.pdf]

LLM Commands
------------

AI-powered analysis (requires ``pip install papercut[llm]``).

summarize
^^^^^^^^^

Generate AI summaries of papers.

.. code-block:: bash

   papercut summarize paper.pdf [OPTIONS]

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

   papercut report paper.pdf [OPTIONS]

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

   papercut study book.pdf [OPTIONS]

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
