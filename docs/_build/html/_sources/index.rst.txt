Papercutter
===========

**Extract knowledge from academic papers** - A CLI-first Python package for researchers.

.. code-block:: bash

   pip install papercutter

.. note::

   Papercutter replaces the former Papercut project. Existing users should review
   :ref:`papercut-migration` for instructions on updating configs, caches, and
   environment variables.

Features
--------

Fetch Papers
~~~~~~~~~~~~

Download from arXiv, DOI, SSRN, NBER, or any URL:

.. code-block:: bash

   papercutter fetch arxiv 2301.00001
   papercutter fetch doi 10.1257/aer.20180779
   papercutter fetch ssrn 3550274
   papercutter fetch url https://example.com/paper.pdf

Extract Content
~~~~~~~~~~~~~~~

Pull text, tables, and references from PDFs:

.. code-block:: bash

   # Extract text (with optional page selection)
   papercutter extract text paper.pdf -p 1-10

   # Extract tables as CSV or JSON
   papercutter extract tables paper.pdf -f csv -o ./tables/

   # Extract references as BibTeX
   papercutter extract refs paper.pdf -o refs.bib

Analyze Structure
~~~~~~~~~~~~~~~~~

Index documents, detect chapters, read by section:

.. code-block:: bash

   # Build document index
   papercutter index paper.pdf

   # Detect chapters in books
   papercutter chapters textbook.pdf

   # Read specific sections
   papercutter read paper.pdf --section "Methods"

AI-Powered Analysis
~~~~~~~~~~~~~~~~~~~

Summarize papers, generate reports, create study aids (requires ``pip install papercutter[llm]``):

.. code-block:: bash

   # Summarize with focus
   papercutter summarize paper.pdf --focus methodology

   # Generate referee report
   papercutter report paper.pdf --template referee

   # Create flashcards from chapter
   papercutter study textbook.pdf --chapter 5 --mode flashcards

Python API
~~~~~~~~~~

Full programmatic access for custom workflows:

.. code-block:: python

   from pathlib import Path
   from papercutter.fetchers.arxiv import ArxivFetcher
   from papercutter.core.text import TextExtractor
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor

   # Fetch a paper
   fetcher = ArxivFetcher()
   doc = fetcher.fetch("2301.00001", Path("./papers"))

   # Extract text
   backend = PdfPlumberExtractor()
   extractor = TextExtractor(backend)
   text = extractor.extract(doc.path)

Quick Links
-----------

- :doc:`installation` - Install Papercutter and optional dependencies
- :doc:`quickstart` - Get started in 5 minutes
- :doc:`tutorial/index` - CLI tutorials
- :doc:`tutorial/python/index` - Python API guide
- :doc:`api/index` - Full API reference

.. toctree::
   :maxdepth: 1
   :caption: Guide
   :hidden:

   installation
   quickstart

.. toctree::
   :maxdepth: 1
   :caption: Tutorials
   :hidden:

   tutorial/index

.. toctree::
   :maxdepth: 1
   :caption: API
   :hidden:

   api/index
