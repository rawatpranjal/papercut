Core Modules
============

The ``papercut.core`` module contains the main content extraction logic for processing PDFs.

.. module:: papercut.core

Text Extraction
---------------

.. module:: papercut.core.text

TextExtractor
~~~~~~~~~~~~~

.. autoclass:: papercut.core.text.TextExtractor
   :members:
   :undoc-members:
   :show-inheritance:

Extracts and processes text content from PDF files.

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.core.text import TextExtractor
   from papercut.extractors.pdfplumber import PdfPlumberExtractor

   # Initialize with a backend
   backend = PdfPlumberExtractor()
   extractor = TextExtractor(backend)

   # Extract full text
   text = extractor.extract(Path("paper.pdf"))

   # Extract chunked for LLM processing
   chunks = extractor.extract_chunked(
       Path("paper.pdf"),
       chunk_size=1000,
       overlap=200
   )
   for chunk in chunks:
       print(f"Chunk {chunk['index']}: {len(chunk['text'])} chars")

Table Extraction
----------------

.. module:: papercut.core.tables

ExtractedTable
~~~~~~~~~~~~~~

.. autoclass:: papercut.core.tables.ExtractedTable
   :members:
   :undoc-members:

Dataclass representing an extracted table from a PDF.

**Attributes:**

- ``page`` (int): Page number where the table was found (0-indexed)
- ``data`` (list[list[Any]]): Raw table data as nested lists
- ``bbox`` (Optional[tuple]): Bounding box coordinates (x0, y0, x1, y1)

**Properties:**

- ``rows`` (int): Number of rows in the table
- ``cols`` (int): Number of columns in the table
- ``headers`` (list[str]): First row as headers

**Example:**

.. code-block:: python

   from papercut.core.tables import ExtractedTable

   table = ExtractedTable(
       page=0,
       data=[
           ["Name", "Age", "City"],
           ["Alice", "30", "NYC"],
           ["Bob", "25", "LA"],
       ]
   )

   print(table.headers)  # ["Name", "Age", "City"]
   print(table.rows)     # 3
   print(table.to_csv())
   # Name,Age,City
   # Alice,30,NYC
   # Bob,25,LA

TableExtractor
~~~~~~~~~~~~~~

.. autoclass:: papercut.core.tables.TableExtractor
   :members:
   :undoc-members:
   :show-inheritance:

Extracts tables from PDF files.

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.core.tables import TableExtractor
   from papercut.extractors.pdfplumber import PdfPlumberExtractor

   backend = PdfPlumberExtractor()
   extractor = TableExtractor(backend)

   tables = extractor.extract(Path("paper.pdf"))
   for table in tables:
       print(f"Table on page {table.page + 1}: {table.rows}x{table.cols}")
       print(table.to_csv())

Reference Extraction
--------------------

.. module:: papercut.core.references

Reference
~~~~~~~~~

.. autoclass:: papercut.core.references.Reference
   :members:
   :undoc-members:

Dataclass representing a parsed bibliographic reference.

**Attributes:**

- ``raw_text`` (str): Original reference text
- ``title`` (Optional[str]): Parsed title
- ``authors`` (list[str]): List of author names
- ``year`` (Optional[int]): Publication year
- ``journal`` (Optional[str]): Journal name
- ``volume`` (Optional[str]): Volume number
- ``pages`` (Optional[str]): Page range
- ``doi`` (Optional[str]): Digital Object Identifier
- ``url`` (Optional[str]): URL if available

**Example:**

.. code-block:: python

   from papercut.core.references import Reference

   ref = Reference(
       raw_text="Smith, J. (2020). A Study. Journal of Studies, 10, 1-20.",
       title="A Study",
       authors=["Smith, J."],
       year=2020,
       journal="Journal of Studies",
       volume="10",
       pages="1-20"
   )

   print(ref.to_bibtex())
   # @article{smith2020,
   #   author = {Smith, J.},
   #   title = {A Study},
   #   journal = {Journal of Studies},
   #   year = {2020},
   #   volume = {10},
   #   pages = {1-20}
   # }

ReferenceExtractor
~~~~~~~~~~~~~~~~~~

.. autoclass:: papercut.core.references.ReferenceExtractor
   :members:
   :undoc-members:
   :show-inheritance:

Extracts and parses bibliographic references from PDF files.

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.core.references import ReferenceExtractor
   from papercut.extractors.pdfplumber import PdfPlumberExtractor

   backend = PdfPlumberExtractor()
   extractor = ReferenceExtractor(backend)

   refs = extractor.extract(Path("paper.pdf"))
   for ref in refs:
       if ref.title:
           print(f"- {ref.title} ({ref.year})")

   # Export all as BibTeX
   bibtex = "\n\n".join(ref.to_bibtex() for ref in refs)
