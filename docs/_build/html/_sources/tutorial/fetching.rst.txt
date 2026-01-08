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
