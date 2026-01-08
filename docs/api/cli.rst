CLI Reference
=============

Papercut provides a command-line interface built with `Typer <https://typer.tiangolo.com/>`_.

Main Command
------------

.. code-block:: bash

   papercut [OPTIONS] COMMAND [ARGS]...

**Options:**

.. option:: --version, -V

   Show version and exit.

.. option:: --help

   Show help message and exit.

Fetch Commands
--------------

Commands for downloading academic papers from various sources.

.. code-block:: bash

   papercut fetch [SOURCE] [ARGS]...

papercut fetch arxiv
~~~~~~~~~~~~~~~~~~~~

Download a paper from arXiv.

.. code-block:: bash

   papercut fetch arxiv PAPER_ID [OPTIONS]

**Arguments:**

.. option:: PAPER_ID

   The arXiv paper ID (e.g., ``2301.00001``).

**Options:**

.. option:: -o, --output DIRECTORY

   Output directory for the downloaded paper.

**Example:**

.. code-block:: bash

   papercut fetch arxiv 2301.00001 -o ./papers

papercut fetch doi
~~~~~~~~~~~~~~~~~~

Download a paper by resolving its DOI.

.. code-block:: bash

   papercut fetch doi IDENTIFIER [OPTIONS]

**Arguments:**

.. option:: IDENTIFIER

   The DOI identifier (e.g., ``10.1257/aer.20180779``).

**Options:**

.. option:: -o, --output DIRECTORY

   Output directory for the downloaded paper.

**Example:**

.. code-block:: bash

   papercut fetch doi 10.1257/aer.20180779 -o ./papers

papercut fetch ssrn
~~~~~~~~~~~~~~~~~~~

Download a paper from SSRN.

.. code-block:: bash

   papercut fetch ssrn PAPER_ID [OPTIONS]

**Arguments:**

.. option:: PAPER_ID

   The SSRN paper ID.

**Options:**

.. option:: -o, --output DIRECTORY

   Output directory for the downloaded paper.

papercut fetch nber
~~~~~~~~~~~~~~~~~~~

Download a paper from NBER.

.. code-block:: bash

   papercut fetch nber PAPER_ID [OPTIONS]

**Arguments:**

.. option:: PAPER_ID

   The NBER working paper ID (e.g., ``w29000`` or ``29000``).

**Options:**

.. option:: -o, --output DIRECTORY

   Output directory for the downloaded paper.

papercut fetch url
~~~~~~~~~~~~~~~~~~

Download a paper from a direct URL.

.. code-block:: bash

   papercut fetch url PAPER_URL [OPTIONS]

**Arguments:**

.. option:: PAPER_URL

   Direct URL to the PDF file.

**Options:**

.. option:: -o, --output DIRECTORY

   Output directory for the downloaded paper.

.. option:: -n, --name FILENAME

   Custom filename for the downloaded paper.

**Example:**

.. code-block:: bash

   papercut fetch url https://example.com/paper.pdf -o ./papers -n my_paper.pdf

Extract Commands
----------------

Commands for extracting content from PDF files.

.. code-block:: bash

   papercut extract [TYPE] [ARGS]...

papercut extract text
~~~~~~~~~~~~~~~~~~~~~

Extract text content from a PDF.

.. code-block:: bash

   papercut extract text PDF_PATH [OPTIONS]

**Arguments:**

.. option:: PDF_PATH

   Path to the PDF file.

**Options:**

.. option:: -o, --output FILE

   Output file path. If not specified, outputs to stdout.

.. option:: -p, --pages RANGE

   Page range to extract (e.g., ``1-5,8,10-12``).

.. option:: --chunk-size SIZE

   Split text into chunks of this token size.

.. option:: --overlap CHARS

   Overlap between chunks in characters (default: 200).

**Examples:**

.. code-block:: bash

   # Extract all text to stdout
   papercut extract text paper.pdf

   # Extract to file
   papercut extract text paper.pdf -o output.txt

   # Extract specific pages
   papercut extract text paper.pdf -p 1-5,10

   # Extract with chunking for LLM
   papercut extract text paper.pdf --chunk-size 1000 --overlap 200

papercut extract tables
~~~~~~~~~~~~~~~~~~~~~~~

Extract tables from a PDF.

.. code-block:: bash

   papercut extract tables PDF_PATH [OPTIONS]

**Arguments:**

.. option:: PDF_PATH

   Path to the PDF file.

**Options:**

.. option:: -o, --output DIRECTORY

   Output directory for extracted tables. If not specified, outputs JSON to stdout.

.. option:: -f, --format FORMAT

   Output format: ``csv`` (default) or ``json``.

.. option:: -p, --pages RANGE

   Page range to extract tables from.

**Examples:**

.. code-block:: bash

   # Extract tables as CSV
   papercut extract tables paper.pdf -o ./tables/

   # Extract as JSON
   papercut extract tables paper.pdf -f json

papercut extract refs
~~~~~~~~~~~~~~~~~~~~~

Extract bibliographic references from a PDF.

.. code-block:: bash

   papercut extract refs PDF_PATH [OPTIONS]

**Arguments:**

.. option:: PDF_PATH

   Path to the PDF file.

**Options:**

.. option:: -o, --output FILE

   Output file path. If not specified, outputs to stdout.

.. option:: -f, --format FORMAT

   Output format: ``bibtex`` (default) or ``json``.

**Examples:**

.. code-block:: bash

   # Extract as BibTeX
   papercut extract refs paper.pdf -o references.bib

   # Extract as JSON
   papercut extract refs paper.pdf -f json -o references.json

Exit Codes
----------

Papercut uses specific exit codes to indicate different error conditions:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Meaning
   * - 0
     - Success
   * - 1
     - General error
   * - 10
     - Fetch error (general)
   * - 11
     - Paper not found
   * - 12
     - Rate limited
   * - 13
     - Network error
   * - 20
     - Extraction error (general)
   * - 21
     - Invalid PDF
   * - 22
     - No content found
   * - 30
     - Configuration error
   * - 31
     - Missing API key
