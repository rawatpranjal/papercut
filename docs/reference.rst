Reference
=========

CLI Commands
------------

ingest
^^^^^^

Digitize PDFs with Docling (PDF -> Markdown + Tables).

.. code-block:: bash

   papercutter ingest <source>

**Arguments:**

- ``source`` - Directory containing PDF files (required)

**Output:**

- ``markdown/`` - Markdown version of each paper
- ``tables/`` - Extracted tables as JSON
- ``figures/`` - Extracted figures
- ``inventory.json`` - Processing status tracker

configure
^^^^^^^^^

Generate extraction schema from paper abstracts.

.. code-block:: bash

   papercutter configure

Samples up to 3 papers and uses LLM to propose extraction fields. Creates ``columns.yaml``.

extract
^^^^^^^

Extract data fields from papers using LLM.

.. code-block:: bash

   papercutter extract

Requires ``columns.yaml`` and ingested papers. Generates ``extractions.json``.

report
^^^^^^

Generate matrix.csv and review.pdf from extractions.

.. code-block:: bash

   papercutter report [--condensed|-c]

**Options:**

- ``--condensed, -c`` - Generate condensed appendix table instead

**Output (standard):**

- ``matrix.csv`` - Flat dataset for R/Stata/Pandas
- ``review.pdf`` - Evidence dossier with one-page summaries

**Output (condensed):**

- ``appendix.csv`` - 4-column summary table
- ``appendix.pdf`` - Condensed appendix

book
^^^^

Process entire books with chapter detection and summarization.

**Subcommands:**

``papercutter book index <pdf>``
   Detect chapter boundaries from PDF outline or text patterns.
   Creates ``book_inventory.json``.

.. code-block:: bash

   papercutter book index ./my-textbook.pdf

``papercutter book extract [--docling|-d]``
   Extract chapter text to ``chapters/`` directory.

.. code-block:: bash

   papercutter book extract

``papercutter book summarize``
   Summarize each chapter with LLM, generate book synthesis.
   Creates ``book_extractions.json``.

.. code-block:: bash

   papercutter book summarize

``papercutter book report``
   Generate ``output/book_summary.pdf`` with one page per chapter.

.. code-block:: bash

   papercutter book report

**Output:**

- ``book_inventory.json`` - Chapter boundaries and processing state
- ``chapters/`` - Extracted chapter text files
- ``book_extractions.json`` - Chapter summaries and book synthesis
- ``output/book_summary.pdf`` - Formatted PDF report

Configuration
-------------

columns.yaml
^^^^^^^^^^^^

Define fields to extract from papers:

.. code-block:: yaml

   columns:
     - key: sample_size
       description: "Total observations (N)"
       type: integer
     - key: method
       description: "Estimation method (OLS, DiD, RDD)"
       type: string
     - key: effect_size
       description: "Main treatment coefficient"
       type: float

**Field properties:**

- ``key`` - Column name in output CSV
- ``description`` - Instructions for LLM extraction
- ``type`` - Data type: ``integer``, ``string``, or ``float``

Output Files
------------

inventory.json
^^^^^^^^^^^^^^

Tracks paper processing status:

.. code-block:: json

   {
     "papers": {
       "paper_id": {
         "id": "...",
         "filename": "...",
         "status": "pending|ingested|extracted"
       }
     }
   }

extractions.json
^^^^^^^^^^^^^^^^

Structured extraction results:

.. code-block:: json

   {
     "executive_summary": "...",
     "papers": [
       {
         "paper_id": "...",
         "title": "...",
         "authors": "...",
         "year": "...",
         "context": "...",
         "method": "...",
         "results": "...",
         "data": {"field1": "value", "field2": 123}
       }
     ]
   }

matrix.csv
^^^^^^^^^^

Flat dataset with one row per paper:

.. code-block:: text

   paper_id,title,sample_size,method,effect_size
   paper1,Study of X,1000,OLS,0.05
   paper2,Analysis of Y,500,DiD,0.12
