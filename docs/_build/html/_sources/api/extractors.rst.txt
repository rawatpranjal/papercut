Extractors
==========

The ``papercut.extractors`` module provides interfaces and implementations for extracting content from PDF files.

Extractor Protocol
------------------

.. module:: papercut.extractors.base

.. class:: Extractor

   Protocol defining the interface for PDF extraction backends.

   All extractor implementations must conform to this protocol.

   **Methods:**

   .. method:: extract_text(path: Path, pages: Optional[list[int]] = None) -> str

      Extract text content from a PDF file.

      :param path: Path to the PDF file
      :param pages: Optional list of 0-indexed page numbers to extract.
                    If None, extracts all pages.
      :returns: Extracted text as a string

      **Example:**

      .. code-block:: python

         from pathlib import Path

         extractor = PdfPlumberExtractor()
         text = extractor.extract_text(Path("paper.pdf"))
         print(text[:500])

         # Extract specific pages (0-indexed)
         text = extractor.extract_text(Path("paper.pdf"), pages=[0, 1, 2])

   .. method:: extract_tables(path: Path, pages: Optional[list[int]] = None) -> list[dict]

      Extract tables from a PDF file.

      :param path: Path to the PDF file
      :param pages: Optional list of 0-indexed page numbers.
                    If None, extracts from all pages.
      :returns: List of dictionaries containing table data

      **Return Format:**

      .. code-block:: python

         [
             {
                 "page": 0,
                 "index": 0,
                 "rows": [
                     ["Header1", "Header2", "Header3"],
                     ["Data1", "Data2", "Data3"],
                 ]
             },
             ...
         ]

      **Example:**

      .. code-block:: python

         tables = extractor.extract_tables(Path("paper.pdf"))
         for table in tables:
             print(f"Table on page {table['page'] + 1}")
             for row in table['rows']:
                 print(row)

   .. method:: get_page_count(path: Path) -> int

      Get the number of pages in a PDF file.

      :param path: Path to the PDF file
      :returns: Number of pages

      **Example:**

      .. code-block:: python

         page_count = extractor.get_page_count(Path("paper.pdf"))
         print(f"Document has {page_count} pages")

Backend Implementations
-----------------------

.. module:: papercut.extractors.pdfplumber

PdfPlumberExtractor
~~~~~~~~~~~~~~~~~~~

.. autoclass:: papercut.extractors.pdfplumber.PdfPlumberExtractor
   :members:
   :undoc-members:
   :show-inheritance:

Default extraction backend using ``pdfplumber``.

**Features:**

- Accurate text extraction
- Good table detection
- Handles complex layouts
- Proper exception handling (InvalidPDFError, ExtractionError)

**Installation:**

Included with base installation:

.. code-block:: bash

   pip install papercut

**Example:**

.. code-block:: python

   from pathlib import Path
   from papercut.extractors.pdfplumber import PdfPlumberExtractor

   extractor = PdfPlumberExtractor()

   # Extract text
   text = extractor.extract_text(Path("paper.pdf"))

   # Extract from specific pages
   text = extractor.extract_text(Path("paper.pdf"), pages=[0, 1, 2])

   # Extract tables
   tables = extractor.extract_tables(Path("paper.pdf"))

   # Get page count
   num_pages = extractor.get_page_count(Path("paper.pdf"))

PyMuPDFExtractor
~~~~~~~~~~~~~~~~

Alternative fast backend using ``pymupdf``.

**Features:**

- Faster processing
- Lower memory usage
- Good for large documents

**Installation:**

.. code-block:: bash

   pip install papercut[fast]

**Configuration:**

Set via environment variable:

.. code-block:: bash

   export PAPERCUT_EXTRACTION__BACKEND=pymupdf

Implementing Custom Extractors
------------------------------

You can implement custom extractors by conforming to the ``Extractor`` protocol:

.. code-block:: python

   from pathlib import Path
   from typing import Optional

   class CustomExtractor:
       """Custom PDF extraction implementation."""

       def extract_text(
           self,
           path: Path,
           pages: Optional[list[int]] = None
       ) -> str:
           # Your implementation here
           pass

       def extract_tables(
           self,
           path: Path,
           pages: Optional[list[int]] = None
       ) -> list[dict]:
           # Your implementation here
           pass

       def get_page_count(self, path: Path) -> int:
           # Your implementation here
           pass

Usage Example
-------------

.. code-block:: python

   from pathlib import Path
   from papercut.config import get_settings

   # Get configured extractor
   settings = get_settings()
   backend = settings.extraction.backend

   if backend == "pdfplumber":
       from papercut.extractors.pdfplumber import PdfPlumberExtractor
       extractor = PdfPlumberExtractor()
   else:
       from papercut.extractors.pymupdf import PyMuPDFExtractor
       extractor = PyMuPDFExtractor()

   # Extract content
   pdf_path = Path("paper.pdf")

   text = extractor.extract_text(pdf_path)
   tables = extractor.extract_tables(pdf_path)
   pages = extractor.get_page_count(pdf_path)

   print(f"Extracted {len(text)} characters from {pages} pages")
   print(f"Found {len(tables)} tables")
