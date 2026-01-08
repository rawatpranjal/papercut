Fetching Papers
===============

Use fetchers programmatically for batch processing, custom workflows, and integration with other tools.

Basic Usage
-----------

.. code-block:: python

   from pathlib import Path
   from papercutter.fetchers.arxiv import ArxivFetcher
   from papercutter.fetchers.doi import DoiFetcher
   from papercutter.fetchers.ssrn import SsrnFetcher
   from papercutter.fetchers.url import UrlFetcher

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
-----------------

The returned ``Document`` object contains metadata:

.. code-block:: python

   from pathlib import Path
   from papercutter.fetchers.arxiv import ArxivFetcher

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
--------------

Process multiple papers in a loop:

.. code-block:: python

   from pathlib import Path
   from papercutter.fetchers.arxiv import ArxivFetcher

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

Error Handling
--------------

Use Papercutter's exception hierarchy for precise error handling:

.. code-block:: python

   from pathlib import Path
   from papercutter.exceptions import (
       FetchError,
       NetworkError,
       PaperNotFoundError,
       RateLimitError,
   )
   from papercutter.fetchers.arxiv import ArxivFetcher

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
----------------------

Automatically select the right fetcher based on the identifier:

.. code-block:: python

   from pathlib import Path
   from papercutter.fetchers.arxiv import ArxivFetcher
   from papercutter.fetchers.doi import DoiFetcher
   from papercutter.fetchers.ssrn import SsrnFetcher
   from papercutter.fetchers.url import UrlFetcher

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
