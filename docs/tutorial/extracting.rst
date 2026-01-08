Extracting Content
==================

Papercutter provides powerful extraction capabilities for PDF documents. This tutorial covers text extraction, table extraction, and reference extraction.

Text Extraction
---------------

Basic Usage
~~~~~~~~~~~

Extract all text from a PDF:

.. code-block:: bash

   # Output to stdout
   papercutter extract text paper.pdf

   # Save to file
   papercutter extract text paper.pdf -o output.txt

Page Selection
~~~~~~~~~~~~~~

Extract text from specific pages using the ``-p`` / ``--pages`` option:

.. code-block:: bash

   # Single page
   papercutter extract text paper.pdf -p 1

   # Page range
   papercutter extract text paper.pdf -p 1-5

   # Multiple ranges and pages
   papercutter extract text paper.pdf -p 1-5,8,10-12

.. note::

   Page numbers are 1-indexed (first page is page 1).

Chunking for LLMs
~~~~~~~~~~~~~~~~~

When preparing text for language model processing, use chunking to split the text into manageable pieces:

.. code-block:: bash

   papercutter extract text paper.pdf --chunk-size 1000 --overlap 200

This outputs JSON with chunked content:

.. code-block:: json

   {
     "chunks": [
       {
         "index": 0,
         "text": "First chunk of text...",
         "start_char": 0,
         "end_char": 1000
       },
       {
         "index": 1,
         "text": "Second chunk with overlap...",
         "start_char": 800,
         "end_char": 1800
       }
     ],
     "total_chunks": 15,
     "chunk_size": 1000,
     "overlap": 200
   }

Parameters:

- ``--chunk-size``: Target size of each chunk in tokens
- ``--overlap``: Number of characters to overlap between chunks (default: 200)

Table Extraction
----------------

Basic Usage
~~~~~~~~~~~

Extract all tables from a PDF:

.. code-block:: bash

   # Output to directory as CSV files
   papercutter extract tables paper.pdf -o ./tables/

   # Output as JSON to stdout
   papercutter extract tables paper.pdf -f json

Output Formats
~~~~~~~~~~~~~~

**CSV Format** (default):

.. code-block:: bash

   papercutter extract tables paper.pdf -f csv -o ./tables/

Creates individual CSV files for each table:

::

   tables/
   ├── table_page1_1.csv
   ├── table_page3_1.csv
   └── table_page3_2.csv

**JSON Format**:

.. code-block:: bash

   papercutter extract tables paper.pdf -f json -o tables.json

Outputs structured JSON:

.. code-block:: json

   {
     "tables": [
       {
         "page": 1,
         "index": 0,
         "rows": [
           ["Header1", "Header2", "Header3"],
           ["Data1", "Data2", "Data3"]
         ]
       }
     ]
   }

Page Selection
~~~~~~~~~~~~~~

Extract tables from specific pages:

.. code-block:: bash

   papercutter extract tables paper.pdf -p 5-10 -o ./tables/

Reference Extraction
--------------------

Extract bibliographic references from the paper.

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   # Output as BibTeX (default)
   papercutter extract refs paper.pdf -o references.bib

   # Output as JSON
   papercutter extract refs paper.pdf -f json -o references.json

BibTeX Format
~~~~~~~~~~~~~

.. code-block:: bash

   papercutter extract refs paper.pdf -f bibtex -o refs.bib

Example output:

.. code-block:: bibtex

   @article{smith2020,
     author = {Smith, John and Doe, Jane},
     title = {A Study of Something Important},
     journal = {Journal of Important Studies},
     year = {2020},
     volume = {10},
     pages = {1-20}
   }

   @book{jones2019,
     author = {Jones, Bob},
     title = {The Complete Guide},
     publisher = {Academic Press},
     year = {2019}
   }

JSON Format
~~~~~~~~~~~

.. code-block:: bash

   papercutter extract refs paper.pdf -f json -o refs.json

Example output:

.. code-block:: json

   {
      "references": [
         {
            "type": "article",
            "authors": ["Smith, John", "Doe, Jane"],
         "title": "A Study of Something Important",
         "journal": "Journal of Important Studies",
         "year": 2020,
         "volume": "10",
         "pages": "1-20"
         }
      ]
   }

Real-World Example: Deriving a Literature Package
-------------------------------------------------

Below is a reproducible sequence using an openly available arXiv paper (``2302.05442``) to produce text chunks, tables, and machine-readable references in a single workspace:

1. **Fetch the paper (if you have not already):**

   .. code-block:: bash

      papercutter fetch arxiv 2302.05442 -o ./workspace

2. **Chunk the text for LLM processing and save the JSON output:**

   .. code-block:: bash

      papercutter extract text ./workspace/Han_2023_small_data.pdf \\
        --chunk-size 1500 --overlap 250 --json -o ./workspace/han_chunks.json

   Sample chunk entry:

   .. code-block:: json

      {
        "index": 4,
        "text": "We evaluate the few-shot performance of the proposed classifier on ...",
        "page_range": [6, 7],
        "overlap": 250
      }

3. **Export every detected table both as CSV (for spreadsheets) and JSON (for scripting):**

   .. code-block:: bash

      papercutter extract tables ./workspace/Han_2023_small_data.pdf \\
        -o ./workspace/tables --format csv

      papercutter extract tables ./workspace/Han_2023_small_data.pdf \\
        -f json -o ./workspace/tables.json

   Directory structure:

   ::

      workspace/
      ├── Han_2023_small_data.pdf
      ├── han_chunks.json
      ├── tables/
      │   ├── table_page4_1.csv
      │   └── table_page5_1.csv
      └── tables.json

4. **Capture citation data to plug into BibTeX or reference managers:**

   .. code-block:: bash

      papercutter extract refs ./workspace/Han_2023_small_data.pdf -o ./workspace/han_refs.bib

   Snippet of the produced BibTeX file:

   .. code-block:: bibtex

      @article{han2023small,
        author = {Han, Jihoon and Lin, Alexandra and others},
        title = {Small-Data Generalization in Transformer Models},
        journal = {arXiv preprint arXiv:2302.05442},
        year = {2023}
      }

This single folder now holds chunks for LLMs, tabular data for spreadsheets, and citations for reference managers—exactly what you need to build briefs, dashboards, or downstream analyses around a specific paper.

Extraction Backend
------------------

Papercutter uses ``pdfplumber`` as the default extraction backend. For faster processing, you can install and use ``pymupdf``:

.. code-block:: bash

   # Install fast backend
   pip install papercutter[fast]

   # Configure via environment variable
   export PAPERCUTTER_EXTRACTION__BACKEND=pymupdf

Tips and Best Practices
-----------------------

1. **Text Quality**: PDF text extraction quality depends on how the PDF was created. Scanned documents may require OCR preprocessing.

2. **Table Detection**: Complex tables with merged cells may not extract perfectly. Review extracted tables for accuracy.

3. **Reference Parsing**: Reference extraction works best with standard bibliography formats. Non-standard citation styles may have lower accuracy.

4. **Large Documents**: For very large PDFs, consider extracting specific page ranges to reduce processing time.

5. **Batch Processing**: Use shell scripting to process multiple files:

   .. code-block:: bash

      for pdf in papers/*.pdf; do
        papercutter extract text "$pdf" -o "text/$(basename "$pdf" .pdf).txt"
      done

.. seealso::

   :doc:`python/extracting` for Python API examples including programmatic extraction, chunking, and batch processing.
