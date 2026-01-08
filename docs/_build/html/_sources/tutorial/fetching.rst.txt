Fetching Papers
===============

Papercutter supports fetching academic papers from multiple sources. This tutorial covers all available fetching methods and their options.

arXiv
-----

arXiv is a popular preprint server for scientific papers. Fetch papers using their arXiv ID:

.. code-block:: bash

   # Standard format
   papercutter fetch arxiv 2301.00001 -o ./papers

   # With category prefix (auto-handled)
   papercutter fetch arxiv cs.AI/2301.00001 -o ./papers

The fetcher automatically extracts metadata including title, authors, and abstract.

DOI Resolution
--------------

Fetch papers using their Digital Object Identifier (DOI):

.. code-block:: bash

   papercutter fetch doi 10.1257/aer.20180779 -o ./papers

Papercutter resolves the DOI to find the actual PDF location and downloads it. This works with most publishers that provide open access or have accessible PDFs.

.. note::

   Some publishers may require institutional access or have paywalls. DOI fetching works best with open access papers.

SSRN
----

The Social Science Research Network (SSRN) hosts working papers in economics, finance, and related fields:

.. code-block:: bash

   papercutter fetch ssrn 3550274 -o ./papers

Provide the SSRN paper ID (the number from the SSRN URL).

NBER
----

The National Bureau of Economic Research (NBER) publishes working papers in economics:

.. code-block:: bash

   # Using the working paper number
   papercutter fetch nber w29000 -o ./papers

   # Just the number also works
   papercutter fetch nber 29000 -o ./papers

Direct URLs
-----------

For papers not covered by the above sources, use direct URL fetching:

.. code-block:: bash

   papercutter fetch url https://example.com/paper.pdf -o ./papers

You can specify a custom filename:

.. code-block:: bash

   papercutter fetch url https://example.com/paper.pdf -o ./papers -n my_paper.pdf

Output Options
--------------

All fetch commands support the ``-o`` / ``--output`` option to specify the output directory:

.. code-block:: bash

   # Save to specific directory
   papercutter fetch arxiv 2301.00001 -o ~/research/papers

   # Save to current directory
   papercutter fetch arxiv 2301.00001 -o .

If not specified, papers are saved to the default output directory configured in settings (default: ``~/papers``).

Document Metadata
-----------------

When fetching papers, Papercutter extracts and stores metadata including:

- **Title** - Paper title
- **Authors** - List of authors
- **Abstract** - Paper abstract (when available)
- **DOI** - Digital Object Identifier
- **arXiv ID** - arXiv identifier (for arXiv papers)
- **Source URL** - Original download URL
- **Fetched At** - Timestamp of download

This metadata is available programmatically when using Papercutter as a library:

.. code-block:: python

   from papercutter.fetchers.base import Document

   # Document is returned by fetch operations
   doc: Document = fetcher.fetch("2301.00001", output_dir)

   print(doc.title)
   print(doc.authors)
   print(doc.abstract)

Error Handling
--------------

Papercutter provides informative error messages for common issues:

- **Paper Not Found** - The paper ID doesn't exist or is invalid
- **Rate Limited** - Too many requests; wait and try again
- **Network Error** - Connection issues; check your internet connection

Example error handling in scripts:

.. code-block:: bash

   papercutter fetch arxiv 2301.00001 -o ./papers || echo "Failed to fetch paper"

.. seealso::

   :doc:`python/fetching` for Python API examples including batch fetching and error handling.

Real-World Example: Building a Reading Stack
--------------------------------------------

This example shows how to pull an actual literature queue of mixed identifiers into a local ``./literature`` folder with metadata sidecars:

1. Create a plain-text list with one identifier per line. Mix and match DOI, arXiv, SSRN, NBER, or URLs:

   .. code-block:: bash

      cat <<'EOF' > reading_list.txt
      # Monetary policy and macro
      arxiv:2206.10140
      doi:10.1257/aer.20190870
      ssrn:4554607
      nber:w30873
      https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2727~e8bbba7d7d.en.pdf
      EOF

2. Run the batch fetcher with async downloads, metadata export, and an explicit output directory:

   .. code-block:: bash

      papercutter fetch batch reading_list.txt --parallel --max-concurrent 4 \\
        --metadata -o ./literature

3. Inspect the results. Papercutter prints a concise summary and drops ``.meta.json`` files next to each PDF:

   .. code-block:: console

      Found 5 paper(s) to fetch
      Downloading 5 papers in parallel...
        Downloaded: Gertler_2022_US_monetary_policy.pdf
        Downloaded: AER_20190870_Kaplan.pdf
        Downloaded: ssrn_4554607.pdf
        Downloaded: nber_w30873.pdf
        Downloaded: ecb_wp2727.pdf

      Done:
        5 downloaded

   Each ``*.meta.json`` contains ready-to-ingest metadata (title, authors, DOI, etc.) so you can load the stack into Zotero, Obsidian, or downstream scripts without extra parsing.
