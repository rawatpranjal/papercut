Configuration
=============

The ``papercut.config`` module provides configuration management using Pydantic Settings.

.. module:: papercut.config.settings

Settings Models
---------------

Settings
~~~~~~~~

.. autoclass:: Settings
   :members:
   :undoc-members:

   Main settings model that aggregates all configuration.

   **Attributes:**

   - ``output`` (OutputSettings): Output directory settings
   - ``extraction`` (ExtractionSettings): PDF extraction settings
   - ``llm`` (LLMSettings): LLM provider settings
   - ``anthropic_api_key`` (Optional[str]): Anthropic API key
   - ``openai_api_key`` (Optional[str]): OpenAI API key

   **Environment Variable Prefix:** ``PAPERCUT_``

   Nested settings use double underscore (``__``) as separator:

   .. code-block:: bash

      PAPERCUT_OUTPUT__DIRECTORY=/path/to/papers
      PAPERCUT_EXTRACTION__BACKEND=pymupdf

OutputSettings
~~~~~~~~~~~~~~

.. autoclass:: OutputSettings
   :members:
   :undoc-members:

   Settings for output directory configuration.

   **Attributes:**

   - ``directory`` (Path): Default output directory for downloaded papers.
     Default: ``~/papers``

ExtractionSettings
~~~~~~~~~~~~~~~~~~

.. autoclass:: ExtractionSettings
   :members:
   :undoc-members:

   Settings for PDF extraction.

   **Attributes:**

   - ``backend`` (str): Extraction backend to use. Default: ``"pdfplumber"``
   - ``text`` (TextExtractionSettings): Text extraction settings
   - ``tables`` (TableExtractionSettings): Table extraction settings

TextExtractionSettings
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: TextExtractionSettings
   :members:
   :undoc-members:

   Settings for text extraction.

   **Attributes:**

   - ``chunk_size`` (Optional[int]): Default chunk size for text chunking.
     None means no chunking.
   - ``chunk_overlap`` (int): Overlap between chunks in characters. Default: 200

TableExtractionSettings
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: TableExtractionSettings
   :members:
   :undoc-members:

   Settings for table extraction.

   **Attributes:**

   - ``format`` (str): Default output format. Default: ``"csv"``

LLMSettings
~~~~~~~~~~~

.. autoclass:: LLMSettings
   :members:
   :undoc-members:

   Settings for LLM integration (v0.2 feature).

   **Attributes:**

   - ``default_provider`` (str): Default LLM provider. Default: ``"anthropic"``
   - ``default_model`` (str): Default model name. Default: ``"claude-sonnet-4-20250514"``
   - ``temperature`` (float): Sampling temperature. Default: 0.1
   - ``max_tokens`` (int): Maximum tokens in response. Default: 4096

Accessing Settings
------------------

get_settings
~~~~~~~~~~~~

.. autofunction:: get_settings

   Get the cached settings instance.

   Settings are loaded once and cached for subsequent calls.

   :returns: Settings instance
   :rtype: Settings

   **Example:**

   .. code-block:: python

      from papercut.config import get_settings

      settings = get_settings()
      print(settings.output.directory)
      print(settings.extraction.backend)

Configuration Sources
---------------------

Settings are loaded from multiple sources in order of precedence:

1. **Environment Variables** (highest priority)

   .. code-block:: bash

      export PAPERCUT_OUTPUT__DIRECTORY=/custom/path
      export PAPERCUT_EXTRACTION__BACKEND=pymupdf
      export ANTHROPIC_API_KEY=sk-ant-...

2. **Configuration File** (future feature)

   ``~/.papercut/config.yaml``

3. **Default Values** (lowest priority)

Environment Variables
---------------------

Common environment variables:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Variable
     - Description
   * - ``PAPERCUT_OUTPUT__DIRECTORY``
     - Default directory for downloaded papers
   * - ``PAPERCUT_EXTRACTION__BACKEND``
     - PDF extraction backend (``pdfplumber`` or ``pymupdf``)
   * - ``PAPERCUT_EXTRACTION__TEXT__CHUNK_SIZE``
     - Default chunk size for text extraction
   * - ``PAPERCUT_EXTRACTION__TEXT__CHUNK_OVERLAP``
     - Overlap between text chunks
   * - ``PAPERCUT_EXTRACTION__TABLES__FORMAT``
     - Default table output format
   * - ``PAPERCUT_LLM__DEFAULT_PROVIDER``
     - Default LLM provider
   * - ``PAPERCUT_LLM__DEFAULT_MODEL``
     - Default LLM model name
   * - ``PAPERCUT_LLM__TEMPERATURE``
     - LLM sampling temperature
   * - ``ANTHROPIC_API_KEY``
     - Anthropic API key
   * - ``OPENAI_API_KEY``
     - OpenAI API key

Example Configuration
---------------------

Set up environment for a research workflow:

.. code-block:: bash

   # Output settings
   export PAPERCUT_OUTPUT__DIRECTORY="$HOME/research/papers"

   # Extraction settings
   export PAPERCUT_EXTRACTION__BACKEND=pdfplumber
   export PAPERCUT_EXTRACTION__TEXT__CHUNK_SIZE=1000
   export PAPERCUT_EXTRACTION__TEXT__CHUNK_OVERLAP=200

   # LLM settings (for future features)
   export PAPERCUT_LLM__DEFAULT_MODEL=claude-sonnet-4-20250514
   export ANTHROPIC_API_KEY=sk-ant-your-key-here

Programmatic Configuration
--------------------------

Access and use settings in Python code:

.. code-block:: python

   from papercut.config import get_settings

   settings = get_settings()

   # Access nested settings
   output_dir = settings.output.directory
   backend = settings.extraction.backend
   chunk_size = settings.extraction.text.chunk_size

   # Check API keys
   if settings.anthropic_api_key:
       print("Anthropic API key configured")

   # Use in your code
   from pathlib import Path

   pdf_path = output_dir / "paper.pdf"
