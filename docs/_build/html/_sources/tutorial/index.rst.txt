Tutorials
=========

Command-Line Interface
----------------------

Learn to use Papercutter from the terminal:

.. toctree::
   :maxdepth: 1

   fetching
   extracting
   indexing
   caching
   llm

Python API
----------

Use Papercutter programmatically for custom workflows:

.. toctree::
   :maxdepth: 1

   python/index
   python/fetching
   python/extracting
   python/workflows

Overview
--------

**CLI Tutorials:**

- :doc:`fetching` - Download papers from arXiv, DOI, SSRN, NBER, URLs
- :doc:`extracting` - Extract text, tables, and references
- :doc:`indexing` - Analyze document structure, detect chapters
- :doc:`caching` - Manage extraction cache
- :doc:`llm` - AI-powered summarization and reports

Each CLI guide now closes with a **Real-World Example** that demonstrates the commands against actual papers and shows representative output so you can copy the workflow directly into your research routine.

**Python API:**

- :doc:`python/index` - Getting started with the Python API
- :doc:`python/fetching` - Programmatic paper fetching
- :doc:`python/extracting` - Programmatic content extraction
- :doc:`python/workflows` - Complete pipelines and LLM integration

Getting Help
------------

For any command, use the ``--help`` flag:

.. code-block:: bash

   papercutter --help
   papercutter fetch --help
   papercutter extract --help
