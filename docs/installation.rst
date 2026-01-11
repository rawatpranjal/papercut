Installation
============

Requirements
------------

- Python 3.10 or higher
- ``OPENAI_API_KEY`` environment variable (for LLM features)

Basic Install
-------------

.. code-block:: bash

   pip install papercutter

This installs core dependencies only (typer, pypdf, pydantic, pyyaml, rich, json-repair).

Full Install
------------

.. code-block:: bash

   pip install papercutter[full]

Includes all optional features: PDF processing, LLM extraction, and report generation.

Optional Dependencies
---------------------

Install only what you need:

.. code-block:: bash

   pip install papercutter[docling]   # PDF to Markdown (Docling)
   pip install papercutter[llm]       # LLM extraction (LiteLLM)
   pip install papercutter[report]    # PDF reports (Jinja2 + LaTeX)

For PDF report generation, you also need LaTeX installed:

.. code-block:: bash

   # macOS
   brew install --cask mactex

   # Ubuntu/Debian
   sudo apt-get install texlive-full

   # Windows
   # Install MiKTeX from https://miktex.org/
