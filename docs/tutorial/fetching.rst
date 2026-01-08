Fetching Papers
===============

Papercut supports fetching academic papers from multiple sources. This tutorial covers all available fetching methods and their options.

arXiv
-----

arXiv is a popular preprint server for scientific papers. Fetch papers using their arXiv ID:

.. code-block:: bash

   # Standard format
   papercut fetch arxiv 2301.00001 -o ./papers

   # With category prefix (auto-handled)
   papercut fetch arxiv cs.AI/2301.00001 -o ./papers

The fetcher automatically extracts metadata including title, authors, and abstract.

DOI Resolution
--------------

Fetch papers using their Digital Object Identifier (DOI):

.. code-block:: bash

   papercut fetch doi 10.1257/aer.20180779 -o ./papers

Papercut resolves the DOI to find the actual PDF location and downloads it. This works with most publishers that provide open access or have accessible PDFs.

.. note::

   Some publishers may require institutional access or have paywalls. DOI fetching works best with open access papers.

SSRN
----

The Social Science Research Network (SSRN) hosts working papers in economics, finance, and related fields:

.. code-block:: bash

   papercut fetch ssrn 3550274 -o ./papers

Provide the SSRN paper ID (the number from the SSRN URL).

NBER
----

The National Bureau of Economic Research (NBER) publishes working papers in economics:

.. code-block:: bash

   # Using the working paper number
   papercut fetch nber w29000 -o ./papers

   # Just the number also works
   papercut fetch nber 29000 -o ./papers

Direct URLs
-----------

For papers not covered by the above sources, use direct URL fetching:

.. code-block:: bash

   papercut fetch url https://example.com/paper.pdf -o ./papers

You can specify a custom filename:

.. code-block:: bash

   papercut fetch url https://example.com/paper.pdf -o ./papers -n my_paper.pdf

Output Options
--------------

All fetch commands support the ``-o`` / ``--output`` option to specify the output directory:

.. code-block:: bash

   # Save to specific directory
   papercut fetch arxiv 2301.00001 -o ~/research/papers

   # Save to current directory
   papercut fetch arxiv 2301.00001 -o .

If not specified, papers are saved to the default output directory configured in settings (default: ``~/papers``).

Document Metadata
-----------------

When fetching papers, Papercut extracts and stores metadata including:

- **Title** - Paper title
- **Authors** - List of authors
- **Abstract** - Paper abstract (when available)
- **DOI** - Digital Object Identifier
- **arXiv ID** - arXiv identifier (for arXiv papers)
- **Source URL** - Original download URL
- **Fetched At** - Timestamp of download

This metadata is available programmatically when using Papercut as a library:

.. code-block:: python

   from papercut.fetchers.base import Document

   # Document is returned by fetch operations
   doc: Document = fetcher.fetch("2301.00001", output_dir)

   print(doc.title)
   print(doc.authors)
   print(doc.abstract)

Error Handling
--------------

Papercut provides informative error messages for common issues:

- **Paper Not Found** - The paper ID doesn't exist or is invalid
- **Rate Limited** - Too many requests; wait and try again
- **Network Error** - Connection issues; check your internet connection

Example error handling in scripts:

.. code-block:: bash

   papercut fetch arxiv 2301.00001 -o ./papers || echo "Failed to fetch paper"

Python API
----------

Using fetchers programmatically allows for batch processing, custom workflows, and integration with other tools.

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.arxiv import ArxivFetcher
   from papercut.fetchers.doi import DoiFetcher
   from papercut.fetchers.ssrn import SsrnFetcher
   from papercut.fetchers.url import UrlFetcher

   output_dir = Path("./papers")

   # ArXiv fetcher
   arxiv = ArxivFetcher()
   if arxiv.can_handle("2301.00001"):
       doc = arxiv.fetch("2301.00001", output_dir)
       print(f"Downloaded: {doc.title}")
       print(f"Authors: {', '.join(doc.authors)}")
       print(f"Saved to: {doc.path}")

   # DOI fetcher
   doi = DoiFetcher()
   doc = doi.fetch("10.1257/aer.20180779", output_dir)

   # SSRN fetcher
   ssrn = SsrnFetcher()
   doc = ssrn.fetch("3550274", output_dir)

   # URL fetcher
   url_fetcher = UrlFetcher()
   doc = url_fetcher.fetch(
       "https://example.com/paper.pdf",
       output_dir,
       filename="my_paper.pdf"  # Optional custom filename
   )

Document Metadata
~~~~~~~~~~~~~~~~~

The returned ``Document`` object contains metadata:

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.arxiv import ArxivFetcher

   fetcher = ArxivFetcher()
   doc = fetcher.fetch("2301.00001", Path("./papers"))

   # Access metadata
   print(f"Title: {doc.title}")
   print(f"Authors: {doc.authors}")
   print(f"Abstract: {doc.abstract}")
   print(f"arXiv ID: {doc.arxiv_id}")
   print(f"DOI: {doc.doi}")
   print(f"Source URL: {doc.source_url}")
   print(f"Fetched at: {doc.fetched_at}")

   # Check if file exists
   print(f"File exists: {doc.exists}")
   print(f"File path: {doc.path}")

Batch Fetching
~~~~~~~~~~~~~~

Process multiple papers in a loop:

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.arxiv import ArxivFetcher

   arxiv_ids = [
       "2301.00001",
       "2301.00002",
       "2301.00003",
       "2301.00004",
   ]

   fetcher = ArxivFetcher()
   output_dir = Path("./papers")
   output_dir.mkdir(exist_ok=True)

   results = []
   for arxiv_id in arxiv_ids:
       try:
           doc = fetcher.fetch(arxiv_id, output_dir)
           results.append({
               "id": arxiv_id,
               "title": doc.title,
               "path": str(doc.path),
               "status": "success"
           })
           print(f"[OK] {doc.title}")
       except Exception as e:
           results.append({
               "id": arxiv_id,
               "status": "failed",
               "error": str(e)
           })
           print(f"[FAIL] {arxiv_id}: {e}")

   # Summary
   success = sum(1 for r in results if r["status"] == "success")
   print(f"\nFetched {success}/{len(arxiv_ids)} papers")

Error Handling in Python
~~~~~~~~~~~~~~~~~~~~~~~~

Use Papercut's exception hierarchy for precise error handling:

.. code-block:: python

   from pathlib import Path
   from papercut.exceptions import (
       FetchError,
       NetworkError,
       PaperNotFoundError,
       RateLimitError,
   )
   from papercut.fetchers.arxiv import ArxivFetcher

   fetcher = ArxivFetcher()

   try:
       doc = fetcher.fetch("invalid-id-12345", Path("./papers"))
   except PaperNotFoundError as e:
       print(f"Paper not found: {e.message}")
       print(f"Hint: {e.hint}")
   except RateLimitError:
       print("Rate limited - waiting before retry...")
   except NetworkError as e:
       print(f"Network issue: {e.message}")
   except FetchError as e:
       print(f"Fetch failed: {e.message}")
       if e.details:
           print(f"Details: {e.details}")

Auto-Detecting Fetcher
~~~~~~~~~~~~~~~~~~~~~~

Automatically select the right fetcher based on the identifier:

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.arxiv import ArxivFetcher
   from papercut.fetchers.doi import DoiFetcher
   from papercut.fetchers.ssrn import SsrnFetcher
   from papercut.fetchers.url import UrlFetcher

   # List of all fetchers
   FETCHERS = [
       ArxivFetcher(),
       DoiFetcher(),
       SsrnFetcher(),
       UrlFetcher(),
   ]

   def fetch_paper(identifier: str, output_dir: Path):
       """Fetch paper using the appropriate fetcher."""
       for fetcher in FETCHERS:
           if fetcher.can_handle(identifier):
               return fetcher.fetch(identifier, output_dir)
       raise ValueError(f"No fetcher found for: {identifier}")

   # Usage
   output_dir = Path("./papers")

   # Automatically uses ArxivFetcher
   doc = fetch_paper("2301.00001", output_dir)

   # Automatically uses DoiFetcher
   doc = fetch_paper("10.1257/aer.20180779", output_dir)

   # Automatically uses UrlFetcher
   doc = fetch_paper("https://example.com/paper.pdf", output_dir)
