Following References
====================

Automatically download papers cited in your source document.

Overview
--------

The ``follow`` command extracts references from a PDF, resolves them
to downloadable identifiers (arXiv IDs, DOIs, URLs), and downloads the papers.

Basic Usage
-----------

Follow all references from a paper:

.. code-block:: bash

   papercutter follow paper.pdf

   papercutter follow paper.pdf -o ./cited_papers/

By default, downloaded papers are saved to ``./cited_papers/``.

Dry Run Mode
------------

Preview what would be downloaded without fetching:

.. code-block:: bash

   papercutter follow paper.pdf --dry-run

Example with "Attention Is All You Need" (arXiv:1706.03762):

.. code-block:: console

   Extracting references from Vaswani_2017_attention_is_all_you_need.pdf...
   Found 40 references
   Resolved 16 to downloadable sources:
     - 16 arxiv
   24 could not be resolved

The dry run also outputs JSON with all resolved identifiers:

.. code-block:: bash

   papercutter follow paper.pdf --dry-run --json

Parallel Downloads
------------------

Speed up downloads with concurrent fetching:

.. code-block:: bash

   papercutter follow paper.pdf --parallel 3 --rate-limit 2.0

Parameters:

- ``--parallel`` / ``-j``: Number of concurrent downloads (default: 1)
- ``--rate-limit``: Delay between downloads in seconds (default: 1.0)

Example with faster downloads:

.. code-block:: bash

   papercutter follow survey.pdf -j 5 --rate-limit 1.0 -o ./library/

Error Handling
--------------

Control behavior on download failures:

.. code-block:: bash

   # Continue after failures (default)
   papercutter follow paper.pdf --continue-on-error

   # Stop on first failure
   papercutter follow paper.pdf --stop-on-error

Manifest Files
--------------

By default, a ``_manifest.json`` is created with full resolution details:

.. code-block:: bash

   cat ./cited_papers/_manifest.json

.. code-block:: json

   {
     "source_pdf": "paper.pdf",
     "timestamp": "2024-01-15T10:30:00",
     "summary": {
       "total_references": 45,
       "resolved": 28,
       "downloaded": 25,
       "failed": 3,
       "unresolved": 17
     },
     "by_source": {
       "arxiv": 15,
       "doi": 10,
       "url": 3
     },
     "references": [
       {
         "raw_text": "Vaswani et al. Attention Is All You Need. arXiv:1706.03762",
         "resolved_id": "1706.03762",
         "source_type": "arxiv",
         "status": "downloaded",
         "local_path": "1706.03762.pdf"
       }
     ]
   }

Disable manifest generation:

.. code-block:: bash

   papercutter follow paper.pdf --no-manifest

Unresolved References
---------------------

References that cannot be resolved are saved to ``_unresolved.txt``:

.. code-block:: bash

   cat ./cited_papers/_unresolved.txt

.. code-block:: text

   # References that could not be resolved to downloadable sources
   # Source: paper.pdf
   # Generated: 2024-01-15T10:30:00

   [1] Smith, J. (2020). Some Book Title. Publisher.
   [2] Conference proceedings without DOI...
   [3] Unpublished manuscript...

These are typically books, old conference papers, or references without
accessible digital versions.

JSON Output
-----------

Get structured output for scripting:

.. code-block:: bash

   papercutter follow paper.pdf --dry-run --json

Example from "Attention Is All You Need":

.. code-block:: json

   {
     "success": true,
     "file": "Vaswani_2017_attention_is_all_you_need.pdf",
     "dry_run": true,
     "total_references": 40,
     "resolved": 16,
     "unresolved": 24,
     "by_source": {
       "arxiv": 16
     },
     "would_download": [
       {"id": "1607.06450", "source": "arxiv"},
       {"id": "1601.06733", "source": "arxiv"},
       {"id": "1610.02357", "source": "arxiv"},
       {"id": "1705.03122v2", "source": "arxiv"},
       {"id": "1308.0850", "source": "arxiv"}
     ]
   }

Real-World Example: Following References from the Transformer Paper
--------------------------------------------------------------------

Download papers cited in "Attention Is All You Need" (arXiv:1706.03762):

1. **Fetch the source paper:**

   .. code-block:: bash

      papercutter fetch arxiv 1706.03762 -o ./papers/

2. **Run dry-run to assess scope:**

   .. code-block:: bash

      papercutter follow ./papers/Vaswani_2017_attention_is_all_you_need.pdf --dry-run

   Output:

   .. code-block:: console

      Found 40 references
      Resolved 16 to downloadable sources:
        - 16 arxiv
      24 could not be resolved

3. **Download resolved references:**

   .. code-block:: bash

      papercutter follow ./papers/Vaswani_2017_attention_is_all_you_need.pdf \
        -o ./cited_papers/ \
        --parallel 3 \
        --rate-limit 1.5

4. **Review the manifest:**

   .. code-block:: bash

      cat ./cited_papers/_manifest.json | jq '.summary'

5. **Check unresolved references:**

   .. code-block:: bash

      cat ./cited_papers/_unresolved.txt

   Unresolved references are typically books, conference papers without DOIs,
   or older papers not available on arXiv.

.. seealso::

   - :doc:`extracting` for extracting references without downloading
   - :doc:`fetching` for manual paper downloads
   - :doc:`../api/resolver` for Python API reference
