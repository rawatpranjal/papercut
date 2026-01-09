Resolver
========

Reference resolution and following.

The resolver module provides tools for extracting downloadable identifiers
(arXiv IDs, DOIs, URLs) from paper references and downloading cited papers.

Reference Resolver
------------------

The resolver extracts identifiers from reference text using pattern matching.

.. autoclass:: papercutter.core.resolver.ResolvedReference
   :members:
   :undoc-members:

.. autoclass:: papercutter.core.resolver.ReferenceResolver
   :members:
   :undoc-members:

Reference Follower
------------------

The follower downloads all cited papers from a source document.

.. autoclass:: papercutter.core.follower.FollowResult
   :members:
   :undoc-members:

.. autoclass:: papercutter.core.follower.FollowProgress
   :members:
   :undoc-members:

.. autoclass:: papercutter.core.follower.ReferenceFollower
   :members:
   :undoc-members:

Example Usage
-------------

Resolve references from a paper:

.. code-block:: python

   from pathlib import Path
   from papercutter.core.references import ReferenceExtractor
   from papercutter.core.resolver import ReferenceResolver
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor

   # Extract references
   extractor = ReferenceExtractor(PdfPlumberExtractor())
   refs = extractor.extract(Path("paper.pdf"))

   # Resolve to downloadable identifiers
   resolver = ReferenceResolver()
   resolved = resolver.resolve_all(refs)

   for ref in resolved:
       if ref.is_resolved:
           print(f"{ref.source_type}: {ref.resolved_id}")

Download all cited papers:

.. code-block:: python

   from pathlib import Path
   from papercutter.core.follower import ReferenceFollower

   follower = ReferenceFollower(
       max_parallel=3,
       rate_limit_delay=1.5,
   )

   result = follower.follow(
       pdf_path=Path("survey.pdf"),
       output_dir=Path("./cited_papers"),
   )

   print(f"Downloaded: {len(result.downloaded)}")
   print(f"Failed: {len(result.failed)}")
   print(f"Unresolved: {len(result.unresolved)}")

.. seealso::

   - :doc:`../tutorial/follow` for CLI usage
   - :doc:`core` for reference extraction
