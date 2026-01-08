API Reference
=============

This section provides detailed API documentation for Papercut's Python modules.

.. toctree::
   :maxdepth: 2

   cli
   core
   fetchers
   extractors
   config
   exceptions

Overview
--------

Papercut is organized into the following main modules:

**CLI** (``papercut.cli``)
   Command-line interface built with Typer. Provides ``fetch`` and ``extract`` commands.

**Core** (``papercut.core``)
   High-level extraction classes for text, tables, and references.

**Fetchers** (``papercut.fetchers``)
   Paper fetching implementations for different sources (arXiv, DOI, SSRN, NBER, URL).

**Extractors** (``papercut.extractors``)
   PDF content extraction using different backends (pdfplumber, pymupdf).

**Config** (``papercut.config``)
   Configuration and settings management using Pydantic.

**Exceptions** (``papercut.exceptions``)
   Custom exception hierarchy with exit codes for CLI error handling.

Using Papercut as a Library
---------------------------

While Papercut is primarily a CLI tool, you can also use it as a Python library:

.. code-block:: python

   from papercut.config import get_settings
   from papercut.fetchers.base import BaseFetcher, Document
   from papercut.extractors.base import Extractor

   # Access settings
   settings = get_settings()
   print(settings.output.directory)

   # Work with documents
   from pathlib import Path
   doc = Document(
       path=Path("paper.pdf"),
       title="My Paper",
       authors=["Author One", "Author Two"]
   )

Module Index
------------

* :ref:`genindex`
* :ref:`modindex`
