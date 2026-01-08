Installation
============

Requirements
------------

Papercutter requires Python 3.10 or later.

Basic Installation
------------------

Install Papercutter using pip:

.. code-block:: bash

   pip install papercutter

Optional Dependencies
---------------------

Papercutter provides optional dependency groups for additional functionality:

**LLM Support**

For LLM-powered features (coming in v0.2):

.. code-block:: bash

   pip install papercutter[llm]

This installs ``litellm`` for multi-provider LLM support.

**Fast PDF Processing**

For faster PDF processing using PyMuPDF:

.. code-block:: bash

   pip install papercutter[fast]

**All Extras**

Install all optional dependencies:

.. code-block:: bash

   pip install papercutter[all]

Development Installation
------------------------

To install Papercutter for development:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/rawatpranjal/papercutter.git
   cd papercutter

   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install in development mode with dev dependencies
   pip install -e ".[dev]"

Configuration
-------------

Papercutter can be configured via environment variables with the ``PAPERCUTTER_`` prefix.

**Common Environment Variables:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``PAPERCUTTER_OUTPUT__DIRECTORY``
     - Default output directory for downloaded papers
   * - ``PAPERCUTTER_EXTRACTION__BACKEND``
     - PDF extraction backend (default: ``pdfplumber``)
   * - ``PAPERCUTTER_LLM__DEFAULT_MODEL``
     - Default LLM model for AI features
   * - ``ANTHROPIC_API_KEY``
     - API key for Anthropic Claude models
   * - ``OPENAI_API_KEY``
     - API key for OpenAI models

Example:

.. code-block:: bash

   export PAPERCUTTER_OUTPUT__DIRECTORY="$HOME/research/papers"
   export PAPERCUTTER_EXTRACTION__BACKEND="pdfplumber"

Verifying Installation
----------------------

After installation, verify that Papercutter is working:

.. code-block:: bash

   # Check version
   papercutter --version

   # View help
   papercutter --help

.. _papercut-migration:

Migrating from Papercut
-----------------------

Papercutter is the renamed successor to Papercut. If you are upgrading an existing environment:

1. Uninstall the old package and install the new one::

      pip uninstall papercut
      pip install papercutter

2. Update shell aliases, scripts, and documentation to call ``papercutter`` instead of ``papercut``.
3. Rename existing config and cache directories if you want to keep previous settings::

      mv ~/.papercut ~/.papercutter
      mv ~/.cache/papercut ~/.cache/papercutter

4. Update any ``PAPERCUT_*`` environment variables to the new ``PAPERCUTTER_*`` prefix (for example ``PAPERCUTTER_ANTHROPIC_API_KEY``).

Once these steps are complete, the CLI, environment variables, and config paths will all align with the new package name.
