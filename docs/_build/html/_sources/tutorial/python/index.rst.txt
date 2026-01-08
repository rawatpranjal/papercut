Python API
==========

Use Papercutter programmatically for custom workflows, batch processing, and integration with other tools.

Installation
------------

.. code-block:: bash

   pip install papercutter

For LLM features:

.. code-block:: bash

   pip install papercutter[llm]

Quick Start
-----------

.. code-block:: python

   from pathlib import Path
   from papercutter.fetchers.arxiv import ArxivFetcher
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.text import TextExtractor

   # Fetch a paper
   fetcher = ArxivFetcher()
   doc = fetcher.fetch("2301.00001", Path("./papers"))
   print(f"Downloaded: {doc.title}")

   # Extract text
   backend = PdfPlumberExtractor()
   extractor = TextExtractor(backend)
   text = extractor.extract(doc.path)
   print(f"Extracted {len(text)} characters")

Tutorials
---------

.. toctree::
   :maxdepth: 1

   fetching
   extracting
   workflows

API Reference
-------------

For complete API documentation, see the :doc:`/api/index`.
