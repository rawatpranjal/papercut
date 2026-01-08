Fetchers
========

The ``papercut.fetchers`` module provides classes for downloading academic papers from various sources.

Base Classes
------------

.. module:: papercut.fetchers.base

Document
~~~~~~~~

.. autoclass:: Document
   :members:
   :undoc-members:
   :show-inheritance:

   A dataclass representing a fetched academic document with its metadata.

   **Attributes:**

   - ``path`` (Path): Path to the downloaded PDF file
   - ``title`` (Optional[str]): Paper title
   - ``authors`` (list[str]): List of author names
   - ``abstract`` (Optional[str]): Paper abstract
   - ``doi`` (Optional[str]): Digital Object Identifier
   - ``arxiv_id`` (Optional[str]): arXiv identifier
   - ``source_url`` (Optional[str]): Original download URL
   - ``fetched_at`` (datetime): Timestamp when the paper was fetched

   **Properties:**

   - ``exists`` (bool): Check if the document file exists on disk

   **Example:**

   .. code-block:: python

      from papercut.fetchers.base import Document
      from pathlib import Path

      doc = Document(
          path=Path("paper.pdf"),
          title="Deep Learning for NLP",
          authors=["John Smith", "Jane Doe"],
          doi="10.1234/example.2024",
      )

      print(doc.title)  # "Deep Learning for NLP"
      print(doc.exists)  # True if file exists

BaseFetcher
~~~~~~~~~~~

.. autoclass:: BaseFetcher
   :members:
   :undoc-members:
   :show-inheritance:

   Abstract base class for paper fetchers.

   All fetcher implementations must inherit from this class and implement
   the abstract methods.

   **Abstract Methods:**

   - ``can_handle(identifier: str) -> bool``: Check if this fetcher can handle the given identifier
   - ``fetch(identifier: str, output_dir: Path, **kwargs) -> Document``: Fetch the paper and return a Document

   **Optional Override:**

   - ``normalize_id(identifier: str) -> str``: Normalize the identifier format

   **Example Implementation:**

   .. code-block:: python

      from papercut.fetchers.base import BaseFetcher, Document
      from pathlib import Path

      class CustomFetcher(BaseFetcher):
          def can_handle(self, identifier: str) -> bool:
              return identifier.startswith("custom:")

          def fetch(self, identifier: str, output_dir: Path, **kwargs) -> Document:
              # Implementation here
              pass

Fetcher Implementations
-----------------------

.. module:: papercut.fetchers.arxiv

ArxivFetcher
~~~~~~~~~~~~

.. autoclass:: papercut.fetchers.arxiv.ArxivFetcher
   :members:
   :undoc-members:
   :show-inheritance:

Fetches papers from arXiv using the arXiv API.

**Supported Identifiers:**

- ``2301.00001`` - New-style arXiv ID
- ``cs.AI/2301.00001`` - With category prefix
- ``hep-th/9901001`` - Old-style arXiv ID

**Features:**

- Automatic metadata extraction (title, authors, abstract, DOI)
- Generates descriptive filenames from paper metadata
- Handles both new and old arXiv ID formats

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.arxiv import ArxivFetcher

   fetcher = ArxivFetcher()

   if fetcher.can_handle("2301.00001"):
       doc = fetcher.fetch("2301.00001", Path("./papers"))
       print(f"Title: {doc.title}")
       print(f"Authors: {doc.authors}")
       print(f"Abstract: {doc.abstract[:200]}...")

.. module:: papercut.fetchers.doi

DOIFetcher
~~~~~~~~~~

.. autoclass:: papercut.fetchers.doi.DOIFetcher
   :members:
   :undoc-members:
   :show-inheritance:

Resolves DOIs and downloads the associated PDF.

**Supported Identifiers:**

- ``10.1257/aer.20180779`` - Standard DOI format
- ``doi:10.1257/aer.20180779`` - With doi: prefix

**Features:**

- CrossRef API integration for metadata
- Unpaywall API for finding open access versions
- Multiple fallback strategies for PDF location
- Generates descriptive filenames

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.doi import DOIFetcher

   fetcher = DOIFetcher()
   doc = fetcher.fetch("10.1257/aer.20180779", Path("./papers"))
   print(f"Downloaded: {doc.title}")

.. module:: papercut.fetchers.ssrn

SSRNFetcher
~~~~~~~~~~~

.. autoclass:: papercut.fetchers.ssrn.SSRNFetcher
   :members:
   :undoc-members:
   :show-inheritance:

Fetches papers from the Social Science Research Network.

**Supported Identifiers:**

- ``3550274`` - SSRN paper ID

**Features:**

- HTML scraping for metadata extraction
- Browser-like headers for reliable downloads
- Automatic filename generation

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.ssrn import SSRNFetcher

   fetcher = SSRNFetcher()
   doc = fetcher.fetch("3550274", Path("./papers"))

.. module:: papercut.fetchers.nber

NBERFetcher
~~~~~~~~~~~

.. autoclass:: papercut.fetchers.nber.NBERFetcher
   :members:
   :undoc-members:
   :show-inheritance:

Fetches working papers from the National Bureau of Economic Research.

**Supported Identifiers:**

- ``w29000`` - With 'w' prefix
- ``29000`` - Numeric only

**Features:**

- Metadata extraction from NBER pages
- Handles multiple ID formats
- Extracts title, authors, and abstract

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.nber import NBERFetcher

   fetcher = NBERFetcher()
   doc = fetcher.fetch("w29000", Path("./papers"))
   # Also works: fetcher.fetch("29000", Path("./papers"))

.. module:: papercut.fetchers.url

URLFetcher
~~~~~~~~~~

.. autoclass:: papercut.fetchers.url.URLFetcher
   :members:
   :undoc-members:
   :show-inheritance:

Downloads papers directly from URLs.

**Supported Identifiers:**

- Any valid HTTP/HTTPS URL

**Features:**

- Direct URL downloads
- Optional custom filename
- Automatic filename extraction from URL
- Rate limit detection

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.url import URLFetcher

   fetcher = URLFetcher()
   doc = fetcher.fetch(
       "https://example.com/paper.pdf",
       Path("./papers"),
       name="custom_name.pdf"  # Optional custom filename
   )

Usage Example
-------------

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.arxiv import ArxivFetcher

   fetcher = ArxivFetcher()
   output_dir = Path("./papers")

   if fetcher.can_handle("2301.00001"):
       doc = fetcher.fetch("2301.00001", output_dir)
       print(f"Downloaded: {doc.title}")
       print(f"Authors: {', '.join(doc.authors)}")
       print(f"Saved to: {doc.path}")
