Papercutter Factory
===================

**Automated Evidence Synthesis Pipeline for Research**

Papercutter Factory transforms unstructured PDF collections into structured datasets
and systematic review reports.

.. code-block:: bash

   pip install papercutter

.. grid:: 1 1 2 2
   :gutter: 2
   :class-container: hero-card-grid

   .. grid-item-card:: 📥 Ingest
      :class-card: sd-bg-primary sd-text-white sd-shadow-sm sd-rounded-3

      Convert PDFs to structured Markdown using Docling. Automatically split
      large volumes, match BibTeX entries, and track processing status.

   .. grid-item-card:: ⚙️ Configure
      :class-card: sd-bg-dark sd-text-white sd-shadow-sm sd-rounded-3

      Define extraction schemas with typed columns. Auto-generate schemas
      from sample papers using LLM analysis.

   .. grid-item-card:: 🔬 Grind
      :class-card: sd-bg-secondary sd-text-white sd-shadow-sm sd-rounded-3

      Extract structured evidence from papers. Pilot mode validates accuracy
      with source quotes before full execution.

   .. grid-item-card:: 📊 Report
      :class-card: sd-bg-light sd-shadow-sm sd-rounded-3

      Generate CSV datasets and LaTeX/Markdown systematic review documents
      with summaries, contribution grids, and more.

Workflow
--------

.. code-block:: bash

   # 1. Initialize project
   papercutter init my_review
   cd my_review

   # 2. Ingest PDFs (with optional BibTeX matching)
   papercutter ingest ./papers/ --bib references.bib

   # 3. Configure extraction schema
   papercutter configure

   # 4. Extract evidence
   papercutter grind --pilot    # Validate on sample
   papercutter grind --full     # Process all papers

   # 5. Generate outputs
   papercutter report

   # Check status anytime
   papercutter status

Project Structure
-----------------

.. code-block:: text

   my_review/
   ├── input/                  # Raw PDF repository
   ├── config.yaml             # Extraction schema
   ├── .papercutter/           # Internal state (Markdown, inventory)
   └── output/
       ├── matrix.csv          # Extracted data for R/Stata/Pandas
       └── systematic_review.pdf

Installation
------------

.. code-block:: bash

   # Basic installation
   pip install papercutter

   # With Docling (recommended for PDF processing)
   pip install papercutter[docling]

   # With all Factory features
   pip install papercutter[factory]

Quick Links
-----------

- :doc:`installation` - Install Papercutter and dependencies
- :doc:`quickstart` - Get started in 5 minutes

.. toctree::
   :maxdepth: 1
   :caption: Guide
   :hidden:

   installation
   quickstart

.. toctree::
   :maxdepth: 1
   :caption: API
   :hidden:

   api/index
