Papercut
========

**Extract knowledge from academic papers**

Papercut is a Python package and CLI tool for downloading academic papers from various sources and extracting structured content from PDFs.

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: Fetch Papers
      :text-align: center

      Download papers from arXiv, DOI, SSRN, NBER, or direct URLs with full metadata extraction.

   .. grid-item-card:: Extract Text
      :text-align: center

      Extract clean text from PDFs with optional chunking for LLM processing.

   .. grid-item-card:: Extract Tables
      :text-align: center

      Extract tables from PDFs and export to CSV or JSON formats.

   .. grid-item-card:: Extract References
      :text-align: center

      Extract bibliographic references and export to BibTeX or JSON.

Installation
------------

.. code-block:: bash

   pip install papercut

Quick Example
-------------

.. code-block:: bash

   # Download a paper from arXiv
   papercut fetch arxiv 2301.00001 -o ./papers

   # Extract text from a PDF
   papercut extract text paper.pdf -o output.txt

   # Extract tables as CSV
   papercut extract tables paper.pdf -o ./tables/

   # Extract references as BibTeX
   papercut extract refs paper.pdf -o references.bib

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: Tutorials
   :hidden:

   tutorial/index

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   :hidden:

   api/index
