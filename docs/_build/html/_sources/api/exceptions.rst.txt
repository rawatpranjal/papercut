Exceptions
==========

The ``papercut.exceptions`` module defines a hierarchy of custom exceptions used throughout Papercut.

.. module:: papercut.exceptions

Exception Hierarchy
-------------------

::

   PapercutError (exit_code=1)
   ├── FetchError (exit_code=10)
   │   ├── PaperNotFoundError (exit_code=11)
   │   ├── RateLimitError (exit_code=12)
   │   └── NetworkError (exit_code=13)
   ├── ExtractionError (exit_code=20)
   │   ├── InvalidPDFError (exit_code=21)
   │   └── NoContentError (exit_code=22)
   ├── ConfigError (exit_code=30)
   │   └── MissingAPIKeyError (exit_code=31)
   └── LLMError (exit_code=40)

Base Exception
--------------

PapercutError
~~~~~~~~~~~~~

.. autoexception:: PapercutError
   :members:
   :show-inheritance:

   Base exception for all Papercut errors.

   **Attributes:**

   - ``message`` (str): Error message
   - ``exit_code`` (int): CLI exit code. Default: 1

   **Example:**

   .. code-block:: python

      from papercut.exceptions import PapercutError

      try:
          # some operation
          pass
      except PapercutError as e:
          print(f"Error: {e}")
          sys.exit(e.exit_code)

Fetch Exceptions
----------------

FetchError
~~~~~~~~~~

.. autoexception:: FetchError
   :members:
   :show-inheritance:

   Base exception for paper fetching errors.

   **Exit Code:** 10

PaperNotFoundError
~~~~~~~~~~~~~~~~~~

.. autoexception:: PaperNotFoundError
   :members:
   :show-inheritance:

   Raised when a paper cannot be found at the specified source.

   **Exit Code:** 11

   **Example:**

   .. code-block:: python

      from papercut.exceptions import PaperNotFoundError

      raise PaperNotFoundError("arXiv paper 9999.99999 not found")

RateLimitError
~~~~~~~~~~~~~~

.. autoexception:: RateLimitError
   :members:
   :show-inheritance:

   Raised when the source API rate limits the request.

   **Exit Code:** 12

   **Example:**

   .. code-block:: python

      from papercut.exceptions import RateLimitError

      raise RateLimitError("arXiv API rate limit exceeded. Try again in 60 seconds.")

NetworkError
~~~~~~~~~~~~

.. autoexception:: NetworkError
   :members:
   :show-inheritance:

   Raised when a network error occurs during fetching.

   **Exit Code:** 13

   **Example:**

   .. code-block:: python

      from papercut.exceptions import NetworkError

      raise NetworkError("Failed to connect to arxiv.org")

Extraction Exceptions
---------------------

ExtractionError
~~~~~~~~~~~~~~~

.. autoexception:: ExtractionError
   :members:
   :show-inheritance:

   Base exception for content extraction errors.

   **Exit Code:** 20

InvalidPDFError
~~~~~~~~~~~~~~~

.. autoexception:: InvalidPDFError
   :members:
   :show-inheritance:

   Raised when the PDF file is invalid or corrupted.

   **Exit Code:** 21

   **Example:**

   .. code-block:: python

      from papercut.exceptions import InvalidPDFError

      raise InvalidPDFError("File is not a valid PDF: paper.pdf")

NoContentError
~~~~~~~~~~~~~~

.. autoexception:: NoContentError
   :members:
   :show-inheritance:

   Raised when no content could be extracted from the PDF.

   **Exit Code:** 22

   **Example:**

   .. code-block:: python

      from papercut.exceptions import NoContentError

      raise NoContentError("No text content found in paper.pdf")

Configuration Exceptions
------------------------

ConfigError
~~~~~~~~~~~

.. autoexception:: ConfigError
   :members:
   :show-inheritance:

   Base exception for configuration errors.

   **Exit Code:** 30

MissingAPIKeyError
~~~~~~~~~~~~~~~~~~

.. autoexception:: MissingAPIKeyError
   :members:
   :show-inheritance:

   Raised when a required API key is not configured.

   **Exit Code:** 31

   **Example:**

   .. code-block:: python

      from papercut.exceptions import MissingAPIKeyError

      raise MissingAPIKeyError("ANTHROPIC_API_KEY not set")

LLM Exception
-------------

LLMError
~~~~~~~~

.. autoexception:: LLMError
   :members:
   :show-inheritance:

   Exception for LLM-related errors (v0.2 feature).

   **Exit Code:** 40

Error Handling Example
----------------------

Handling exceptions in scripts:

.. code-block:: python

   import sys
   from papercut.exceptions import (
       PapercutError,
       PaperNotFoundError,
       RateLimitError,
       NetworkError,
   )

   def fetch_paper(paper_id: str) -> None:
       try:
           # fetch logic here
           pass
       except PaperNotFoundError:
           print(f"Paper {paper_id} not found")
           sys.exit(11)
       except RateLimitError:
           print("Rate limited. Please wait and try again.")
           sys.exit(12)
       except NetworkError as e:
           print(f"Network error: {e}")
           sys.exit(13)
       except PapercutError as e:
           print(f"Error: {e}")
           sys.exit(e.exit_code)

CLI Error Handling
------------------

The CLI automatically handles exceptions and returns appropriate exit codes:

.. code-block:: bash

   # Check exit code after command
   papercut fetch arxiv invalid_id
   echo $?  # Returns 11 (PaperNotFoundError)

   # Use in scripts
   if ! papercut fetch arxiv 2301.00001 -o ./papers; then
       echo "Failed to fetch paper"
   fi
