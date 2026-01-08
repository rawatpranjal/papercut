Quickstart
==========

This guide will walk you through the basic workflow of using Papercutter to fetch academic papers and extract content from them.

Fetching a Paper
----------------

Download a paper from arXiv using its paper ID:

.. code-block:: bash

   papercutter fetch arxiv 2301.00001 -o ./papers

This downloads the paper and saves it to the ``./papers`` directory.

You can also fetch papers using DOI:

.. code-block:: bash

   papercutter fetch doi 10.1257/aer.20180779 -o ./papers

Extracting Text
---------------

Extract the full text content from a PDF:

.. code-block:: bash

   papercutter extract text paper.pdf

To save the output to a file:

.. code-block:: bash

   papercutter extract text paper.pdf -o output.txt

Extract text from specific pages:

.. code-block:: bash

   papercutter extract text paper.pdf -p 1-5,10

Chunking for LLM Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When preparing text for language models, you can chunk the output:

.. code-block:: bash

   papercutter extract text paper.pdf --chunk-size 1000 --overlap 200

This outputs JSON with chunked text suitable for embedding or LLM processing.

Extracting Tables
-----------------

Extract all tables from a PDF:

.. code-block:: bash

   papercutter extract tables paper.pdf -o ./tables/

By default, tables are saved as CSV files. Use JSON format instead:

.. code-block:: bash

   papercutter extract tables paper.pdf -f json -o ./tables/

Extract tables from specific pages:

.. code-block:: bash

   papercutter extract tables paper.pdf -p 5-10 -o ./tables/

Extracting References
---------------------

Extract bibliographic references as BibTeX:

.. code-block:: bash

   papercutter extract refs paper.pdf -o references.bib

Or as JSON:

.. code-block:: bash

   papercutter extract refs paper.pdf -f json -o references.json

Complete Workflow Example
-------------------------

Here's a complete example workflow for processing an academic paper:

.. code-block:: bash

   # 1. Create a working directory
   mkdir -p research/paper_analysis
   cd research/paper_analysis

   # 2. Download a paper from arXiv
   papercutter fetch arxiv 2301.00001 -o .

   # 3. Extract the full text
   papercutter extract text 2301.00001.pdf -o text.txt

   # 4. Extract tables to CSV files
   papercutter extract tables 2301.00001.pdf -o tables/

   # 5. Extract references
   papercutter extract refs 2301.00001.pdf -o references.bib

   # 6. View the results
   ls -la
   # Output:
   # 2301.00001.pdf
   # text.txt
   # references.bib
   # tables/
   #   table_1.csv
   #   table_2.csv

Next Steps
----------

- See :doc:`tutorial/fetching` for detailed information on fetching papers from different sources
- See :doc:`tutorial/extracting` for advanced extraction options
- See :doc:`api/index` for the complete API reference
