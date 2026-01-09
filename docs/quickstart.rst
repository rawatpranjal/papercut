Quickstart
==========

This guide walks you through the Papercutter Factory workflow for systematic literature reviews.

Prerequisites
-------------

- Python 3.10+
- An API key for OpenAI or Anthropic (for LLM features)

.. code-block:: bash

   pip install papercutter[factory]
   export OPENAI_API_KEY=sk-...  # or ANTHROPIC_API_KEY

Step 1: Initialize Project
--------------------------

Create a new review project:

.. code-block:: bash

   papercutter init my_review
   cd my_review

This creates:

.. code-block:: text

   my_review/
   ├── input/              # Place your PDFs here
   └── .papercutter/       # Project state

Step 2: Ingest PDFs
-------------------

Add your PDFs to the ``input/`` folder, then run:

.. code-block:: bash

   papercutter ingest

With BibTeX matching:

.. code-block:: bash

   papercutter ingest --bib references.bib

The ingest phase:

- Converts PDFs to structured Markdown using Docling
- Splits large volumes (500+ pages) into chapters
- Matches papers to BibTeX entries
- Tracks processing status

Check progress:

.. code-block:: bash

   papercutter status

Step 3: Configure Schema
------------------------

Define what data to extract:

.. code-block:: bash

   papercutter configure

This analyzes sample papers and generates a schema. Edit ``config.yaml`` to customize:

.. code-block:: yaml

   columns:
     - key: sample_size
       description: "Total observations (N)"
       type: integer
     - key: estimation_method
       description: "Statistical method (DiD, RDD, OLS)"
       type: string
     - key: treatment_effect
       description: "Main treatment coefficient"
       type: float

Or use a template:

.. code-block:: bash

   papercutter configure --template economics

Step 4: Extract Evidence
------------------------

Run pilot mode to validate:

.. code-block:: bash

   papercutter grind --pilot

This processes 5 random papers and generates ``pilot_trace.csv`` with source quotes for verification.

Once validated, run full extraction:

.. code-block:: bash

   papercutter grind --full

Step 5: Generate Report
-----------------------

Create outputs:

.. code-block:: bash

   papercutter report

This generates:

- ``output/matrix.csv`` - Extracted data for R/Stata/Pandas
- ``output/systematic_review.pdf`` - LaTeX document with summaries

Common Options
--------------

.. code-block:: bash

   # Verbose output
   papercutter --verbose ingest

   # Quiet mode
   papercutter --quiet grind --full

   # Check version
   papercutter --version

Troubleshooting
---------------

**No papers found after ingest:**

Check that PDFs are in the ``input/`` folder and run ``papercutter status``.

**Docling errors:**

Papercutter falls back to OCR extraction if Docling fails. Install Tesseract for better results.

**LLM errors:**

Ensure your API key is set: ``export OPENAI_API_KEY=sk-...``

Next Steps
----------

- Review ``config.yaml`` and customize the extraction schema
- Check ``pilot_trace.csv`` to verify extraction accuracy
- Edit summaries in the generated report as needed
