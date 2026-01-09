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

This outputs JSON with chunked content. Example from "Attention Is All You Need":

.. code-block:: json

   {
     "success": true,
     "file": "Vaswani_2017_attention_is_all_you_need.pdf",
     "chunked": true,
     "chunk_size": 500,
     "overlap": 100,
     "count": 29,
     "chunks": [
       "Attention Is All You Need...",
       "Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit...",
       "Abstract: The dominant sequence transduction models are based on..."
     ]
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
   papercutter extract tables paper.pdf --json

Output Formats
~~~~~~~~~~~~~~

**CSV Format** (default with ``-o``):

.. code-block:: bash

   papercutter extract tables paper.pdf -o ./tables/

Creates individual CSV files for each table:

::

   tables/
   ├── table_page1_1.csv
   ├── table_page3_1.csv
   └── table_page3_2.csv

**JSON Format** (use ``--json`` flag):

.. code-block:: bash

   papercutter extract tables paper.pdf --json

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

Section Extraction
------------------

Extract text from specific named sections of a document.

List Sections
~~~~~~~~~~~~~

View all detected sections in a paper:

.. code-block:: bash

   papercutter extract section paper.pdf --list

Example from "Attention Is All You Need" (arXiv:1706.03762):

.. code-block:: json

   {
     "success": true,
     "file": "Vaswani_2017_attention_is_all_you_need.pdf",
     "count": 9,
     "sections": [
       {"id": 1, "title": "Abstract", "pages": [1, 1]},
       {"id": 2, "title": "1   Introduction", "pages": [2, 2]},
       {"id": 3, "title": "3.1   Encoder and Decoder Stacks", "pages": [3, 4]},
       {"id": 4, "title": "3.3   Position-wise Feed-Forward Networks", "pages": [5, 5]},
       {"id": 5, "title": "3.5   Positional Encoding", "pages": [6, 6]},
       {"id": 6, "title": "5.1   Training Data and Batching", "pages": [7, 7]},
       {"id": 7, "title": "6   Results", "pages": [8, 8]},
       {"id": 8, "title": "6.3   English Constituency Parsing", "pages": [9, 9]},
       {"id": 9, "title": "7   Conclusion", "pages": [10, 15]}
     ]
   }

Extract a Section
~~~~~~~~~~~~~~~~~

Extract text from a specific section by name (partial match supported):

.. code-block:: bash

   papercutter extract section paper.pdf --section "Methods"

   # Partial match works
   papercutter extract section paper.pdf -s "Intro"

Or by section ID:

.. code-block:: bash

   papercutter extract section paper.pdf -s 3

Save to file:

.. code-block:: bash

   papercutter extract section paper.pdf -s Introduction -o intro.txt

.. note::

   Section detection works best with papers that have clear heading structure.
   For books with chapters, use ``papercutter chapters`` instead.

Real-World Example: Extracting Content from "Attention Is All You Need"
------------------------------------------------------------------------

Below is a reproducible sequence using the famous Transformer paper (arXiv:1706.03762):

1. **Fetch the paper:**

   .. code-block:: bash

      papercutter fetch arxiv 1706.03762 -o ./workspace

2. **Chunk the text for LLM processing:**

   .. code-block:: bash

      papercutter extract text ./workspace/Vaswani_2017_attention_is_all_you_need.pdf \
        --chunk-size 500 --overlap 100 -p 1-2 --json -o ./workspace/chunks.json

   Output shows 29 chunks from the first 2 pages.

3. **Extract tables:**

   .. code-block:: bash

      papercutter extract tables ./workspace/Vaswani_2017_attention_is_all_you_need.pdf \
        -o ./workspace/tables/

   The paper has 6 tables (experimental results).

4. **Extract references:**

   .. code-block:: bash

      papercutter extract refs ./workspace/Vaswani_2017_attention_is_all_you_need.pdf \
        -o ./workspace/refs.bib

   Extracts 40 references to BibTeX format.

5. **List detected sections:**

   .. code-block:: bash

      papercutter extract section ./workspace/Vaswani_2017_attention_is_all_you_need.pdf --list

   Shows 9 detected sections including Abstract, Introduction, Results, and Conclusion.

   Directory structure after extraction:

   ::

      workspace/
      ├── Vaswani_2017_attention_is_all_you_need.pdf
      ├── chunks.json
      ├── tables/
      │   ├── table_1.csv
      │   └── ...
      └── refs.bib

This workspace now contains chunks for LLMs, tabular data, and references—ready for downstream analysis.

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

5. **LLM-Ready Chunks**: Use ``--include-metadata`` with ``--chunk-size`` for chunks that include page numbers, section context, and figure/table references:

   .. code-block:: bash

      papercutter extract text paper.pdf --chunk-size 2000 --include-metadata

6. **Batch Processing**: Process multiple PDFs using the built-in batch mode:

   .. code-block:: bash

      # Create a file listing PDFs to process
      ls papers/*.pdf > pdfs.txt

      # Batch extract to directory
      papercutter extract text --batch pdfs.txt -o ./output/

   See :doc:`fetching` for batch fetching with ``--batch`` and ``--metadata`` options.

.. seealso::

   :doc:`python/extracting` for Python API examples including programmatic extraction, chunking, and batch processing.
