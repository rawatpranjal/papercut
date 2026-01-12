Papercutter
===========

Extract structured data from academic papers.

.. code-block:: bash

   pip install papercutter[full]

----

Pipeline
--------

.. grid:: 2 2 2 2
   :gutter: 3

   .. grid-item-card:: 1. Ingest
      :link: quickstart.html#ingest

      ``papercutter ingest ./pdfs/``

      Convert PDFs to Markdown using Docling. Extracts tables and figures.

   .. grid-item-card:: 2. Configure
      :link: quickstart.html#configure

      ``papercutter configure``

      Generate ``columns.yaml`` schema from paper abstracts.

   .. grid-item-card:: 3. Grind
      :link: quickstart.html#grind

      ``papercutter grind``

      Extract structured data from each paper using LLM.

   .. grid-item-card:: 4. Report
      :link: quickstart.html#report

      ``papercutter report``

      Output ``matrix.csv`` and ``review.pdf``.

----

Features
--------

- **Batch processing** — Process entire PDF collections with per-file status tracking
- **Table extraction** — Preserve tabular data structure via Docling
- **Schema validation** — Define typed extraction fields in YAML
- **Book support** — Chapter detection and summarization for handbooks

----

Quick Example
-------------

.. code-block:: bash

   export OPENAI_API_KEY="sk-..."

   papercutter ingest ./papers/
   papercutter configure
   papercutter grind
   papercutter report

Outputs ``matrix.csv`` (for R/Stata) and ``review.pdf`` (LaTeX report).

----

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   installation
   quickstart
   tutorial
   reference
