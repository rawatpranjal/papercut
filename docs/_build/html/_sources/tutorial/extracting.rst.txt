Extracting Content
==================

Papercut provides powerful extraction capabilities for PDF documents. This tutorial covers text extraction, table extraction, and reference extraction.

Text Extraction
---------------

Basic Usage
~~~~~~~~~~~

Extract all text from a PDF:

.. code-block:: bash

   # Output to stdout
   papercut extract text paper.pdf

   # Save to file
   papercut extract text paper.pdf -o output.txt

Page Selection
~~~~~~~~~~~~~~

Extract text from specific pages using the ``-p`` / ``--pages`` option:

.. code-block:: bash

   # Single page
   papercut extract text paper.pdf -p 1

   # Page range
   papercut extract text paper.pdf -p 1-5

   # Multiple ranges and pages
   papercut extract text paper.pdf -p 1-5,8,10-12

.. note::

   Page numbers are 1-indexed (first page is page 1).

Chunking for LLMs
~~~~~~~~~~~~~~~~~

When preparing text for language model processing, use chunking to split the text into manageable pieces:

.. code-block:: bash

   papercut extract text paper.pdf --chunk-size 1000 --overlap 200

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
   papercut extract tables paper.pdf -o ./tables/

   # Output as JSON to stdout
   papercut extract tables paper.pdf -f json

Output Formats
~~~~~~~~~~~~~~

**CSV Format** (default):

.. code-block:: bash

   papercut extract tables paper.pdf -f csv -o ./tables/

Creates individual CSV files for each table:

::

   tables/
   ├── table_page1_1.csv
   ├── table_page3_1.csv
   └── table_page3_2.csv

**JSON Format**:

.. code-block:: bash

   papercut extract tables paper.pdf -f json -o tables.json

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

   papercut extract tables paper.pdf -p 5-10 -o ./tables/

Reference Extraction
--------------------

Extract bibliographic references from the paper.

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   # Output as BibTeX (default)
   papercut extract refs paper.pdf -o references.bib

   # Output as JSON
   papercut extract refs paper.pdf -f json -o references.json

BibTeX Format
~~~~~~~~~~~~~

.. code-block:: bash

   papercut extract refs paper.pdf -f bibtex -o refs.bib

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

   papercut extract refs paper.pdf -f json -o refs.json

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

Extraction Backend
------------------

Papercut uses ``pdfplumber`` as the default extraction backend. For faster processing, you can install and use ``pymupdf``:

.. code-block:: bash

   # Install fast backend
   pip install papercut[fast]

   # Configure via environment variable
   export PAPERCUT_EXTRACTION__BACKEND=pymupdf

Tips and Best Practices
-----------------------

1. **Text Quality**: PDF text extraction quality depends on how the PDF was created. Scanned documents may require OCR preprocessing.

2. **Table Detection**: Complex tables with merged cells may not extract perfectly. Review extracted tables for accuracy.

3. **Reference Parsing**: Reference extraction works best with standard bibliography formats. Non-standard citation styles may have lower accuracy.

4. **Large Documents**: For very large PDFs, consider extracting specific page ranges to reduce processing time.

5. **Batch Processing**: Use shell scripting to process multiple files:

   .. code-block:: bash

      for pdf in papers/*.pdf; do
        papercut extract text "$pdf" -o "text/$(basename "$pdf" .pdf).txt"
      done
