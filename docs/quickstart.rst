Quickstart
==========

This guide walks through extracting structured data from a collection of PDFs.

Setup
-----

1. Install papercutter with all features:

.. code-block:: bash

   pip install papercutter[full]

2. Set your OpenAI API key:

.. code-block:: bash

   export OPENAI_API_KEY="sk-..."

3. Create a project directory with your PDFs:

.. code-block:: bash

   mkdir my-review
   cd my-review
   # Copy your PDFs here

The Pipeline
------------

.. _ingest:

**Step 1: Ingest PDFs**

Convert PDFs to Markdown and extract tables:

.. code-block:: bash

   papercutter ingest ./

This creates:

- ``markdown/`` - Markdown version of each paper
- ``tables/`` - Extracted tables as JSON
- ``figures/`` - Extracted figures
- ``inventory.json`` - Tracks processing status

.. _configure:

**Step 2: Configure Schema**

Generate an extraction schema from your papers:

.. code-block:: bash

   papercutter configure

The LLM samples your papers and proposes fields to extract. Edit ``columns.yaml`` to customize:

.. code-block:: yaml

   columns:
     - key: sample_size
       description: "Total observations (N)"
       type: integer
     - key: method
       description: "Estimation method"
       type: string

.. _extract:

**Step 3: Extract Data**

Run LLM extraction on all papers:

.. code-block:: bash

   papercutter extract

This generates ``extractions.json`` with structured data from each paper.

.. _report:

**Step 4: Generate Reports**

Create the final outputs:

.. code-block:: bash

   papercutter report

Outputs:

- ``matrix.csv`` - Flat dataset for R/Stata/Pandas
- ``review.pdf`` - Evidence dossier with one-page summaries

For a condensed appendix view:

.. code-block:: bash

   papercutter report --condensed
