Installation
============

Requirements
------------

Papercut requires Python 3.10 or later.

Basic Installation
------------------

Install Papercut using pip:

.. code-block:: bash

   pip install papercut

Optional Dependencies
---------------------

Papercut provides optional dependency groups for additional functionality:

**LLM Support**

For LLM-powered features (coming in v0.2):

.. code-block:: bash

   pip install papercut[llm]

This installs ``litellm`` for multi-provider LLM support.

**Fast PDF Processing**

For faster PDF processing using PyMuPDF:

.. code-block:: bash

   pip install papercut[fast]

**All Extras**

Install all optional dependencies:

.. code-block:: bash

   pip install papercut[all]

Development Installation
------------------------

To install Papercut for development:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/pranjalrawat007/papercut.git
   cd papercut

   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install in development mode with dev dependencies
   pip install -e ".[dev]"

Configuration
-------------

Papercut can be configured via environment variables with the ``PAPERCUT_`` prefix.

**Common Environment Variables:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Description
   * - ``PAPERCUT_OUTPUT__DIRECTORY``
     - Default output directory for downloaded papers
   * - ``PAPERCUT_EXTRACTION__BACKEND``
     - PDF extraction backend (default: ``pdfplumber``)
   * - ``PAPERCUT_LLM__DEFAULT_MODEL``
     - Default LLM model for AI features
   * - ``ANTHROPIC_API_KEY``
     - API key for Anthropic Claude models
   * - ``OPENAI_API_KEY``
     - API key for OpenAI models

Example:

.. code-block:: bash

   export PAPERCUT_OUTPUT__DIRECTORY="$HOME/research/papers"
   export PAPERCUT_EXTRACTION__BACKEND="pdfplumber"

Verifying Installation
----------------------

After installation, verify that Papercut is working:

.. code-block:: bash

   # Check version
   papercut --version

   # View help
   papercut --help
