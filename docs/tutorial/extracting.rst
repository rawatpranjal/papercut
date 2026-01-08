Extracting Content
==================

Papercut provides powerful extraction capabilities for PDF documents. This tutorial covers text extraction, table extraction, and reference extraction.

Text Extraction
---------------

Basic Usage
~~~~~~~~~~~

Extract all text from a PDF:

.. code-block:: bash

   # Output to stdout
   papercut extract text paper.pdf

   # Save to file
   papercut extract text paper.pdf -o output.txt

Page Selection
~~~~~~~~~~~~~~

Extract text from specific pages using the ``-p`` / ``--pages`` option:

.. code-block:: bash

   # Single page
   papercut extract text paper.pdf -p 1

   # Page range
   papercut extract text paper.pdf -p 1-5

   # Multiple ranges and pages
   papercut extract text paper.pdf -p 1-5,8,10-12

.. note::

   Page numbers are 1-indexed (first page is page 1).

Chunking for LLMs
~~~~~~~~~~~~~~~~~

When preparing text for language model processing, use chunking to split the text into manageable pieces:

.. code-block:: bash

   papercut extract text paper.pdf --chunk-size 1000 --overlap 200

This outputs JSON with chunked content:

.. code-block:: json

   {
     "chunks": [
       {
         "index": 0,
         "text": "First chunk of text...",
         "start_char": 0,
         "end_char": 1000
       },
       {
         "index": 1,
         "text": "Second chunk with overlap...",
         "start_char": 800,
         "end_char": 1800
       }
     ],
     "total_chunks": 15,
     "chunk_size": 1000,
     "overlap": 200
   }

Parameters:

- ``--chunk-size``: Target size of each chunk in tokens
- ``--overlap``: Number of characters to overlap between chunks (default: 200)

Table Extraction
----------------

Basic Usage
~~~~~~~~~~~

Extract all tables from a PDF:

.. code-block:: bash

   # Output to directory as CSV files
   papercut extract tables paper.pdf -o ./tables/

   # Output as JSON to stdout
   papercut extract tables paper.pdf -f json

Output Formats
~~~~~~~~~~~~~~

**CSV Format** (default):

.. code-block:: bash

   papercut extract tables paper.pdf -f csv -o ./tables/

Creates individual CSV files for each table:

::

   tables/
   ├── table_page1_1.csv
   ├── table_page3_1.csv
   └── table_page3_2.csv

**JSON Format**:

.. code-block:: bash

   papercut extract tables paper.pdf -f json -o tables.json

Outputs structured JSON:

.. code-block:: json

   {
     "tables": [
       {
         "page": 1,
         "index": 0,
         "rows": [
           ["Header1", "Header2", "Header3"],
           ["Data1", "Data2", "Data3"]
         ]
       }
     ]
   }

Page Selection
~~~~~~~~~~~~~~

Extract tables from specific pages:

.. code-block:: bash

   papercut extract tables paper.pdf -p 5-10 -o ./tables/

Reference Extraction
--------------------

Extract bibliographic references from the paper.

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   # Output as BibTeX (default)
   papercut extract refs paper.pdf -o references.bib

   # Output as JSON
   papercut extract refs paper.pdf -f json -o references.json

BibTeX Format
~~~~~~~~~~~~~

.. code-block:: bash

   papercut extract refs paper.pdf -f bibtex -o refs.bib

Example output:

.. code-block:: bibtex

   @article{smith2020,
     author = {Smith, John and Doe, Jane},
     title = {A Study of Something Important},
     journal = {Journal of Important Studies},
     year = {2020},
     volume = {10},
     pages = {1-20}
   }

   @book{jones2019,
     author = {Jones, Bob},
     title = {The Complete Guide},
     publisher = {Academic Press},
     year = {2019}
   }

JSON Format
~~~~~~~~~~~

.. code-block:: bash

   papercut extract refs paper.pdf -f json -o refs.json

Example output:

.. code-block:: json

   {
     "references": [
       {
         "type": "article",
         "authors": ["Smith, John", "Doe, Jane"],
         "title": "A Study of Something Important",
         "journal": "Journal of Important Studies",
         "year": 2020,
         "volume": "10",
         "pages": "1-20"
       }
     ]
   }

Extraction Backend
------------------

Papercut uses ``pdfplumber`` as the default extraction backend. For faster processing, you can install and use ``pymupdf``:

.. code-block:: bash

   # Install fast backend
   pip install papercut[fast]

   # Configure via environment variable
   export PAPERCUT_EXTRACTION__BACKEND=pymupdf

Tips and Best Practices
-----------------------

1. **Text Quality**: PDF text extraction quality depends on how the PDF was created. Scanned documents may require OCR preprocessing.

2. **Table Detection**: Complex tables with merged cells may not extract perfectly. Review extracted tables for accuracy.

3. **Reference Parsing**: Reference extraction works best with standard bibliography formats. Non-standard citation styles may have lower accuracy.

4. **Large Documents**: For very large PDFs, consider extracting specific page ranges to reduce processing time.

5. **Batch Processing**: Use shell scripting to process multiple files:

   .. code-block:: bash

      for pdf in papers/*.pdf; do
        papercut extract text "$pdf" -o "text/$(basename "$pdf" .pdf).txt"
      done

Python API
----------

Using extractors programmatically gives you full control and allows integration with other tools.

Setting Up Extractors
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from papercut.extractors.pdfplumber import PdfPlumberExtractor
   from papercut.core.text import TextExtractor
   from papercut.core.tables import TableExtractor
   from papercut.core.references import ReferenceExtractor

   # Initialize the backend (pdfplumber is the default)
   backend = PdfPlumberExtractor()

   # Create specialized extractors
   text_extractor = TextExtractor(backend)
   table_extractor = TableExtractor(backend)
   ref_extractor = ReferenceExtractor(backend)

Text Extraction
~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from papercut.extractors.pdfplumber import PdfPlumberExtractor
   from papercut.core.text import TextExtractor

   backend = PdfPlumberExtractor()
   extractor = TextExtractor(backend)

   # Extract all text
   text = extractor.extract(Path("paper.pdf"))
   print(f"Extracted {len(text)} characters")

   # Extract from specific pages (0-indexed)
   intro_text = extractor.extract(Path("paper.pdf"), pages=[0, 1, 2])
   print(f"Introduction: {intro_text[:200]}...")

Chunking for LLMs
~~~~~~~~~~~~~~~~~

The chunker is sentence-aware and avoids breaking mid-sentence:

.. code-block:: python

   from pathlib import Path
   from papercut.extractors.pdfplumber import PdfPlumberExtractor
   from papercut.core.text import TextExtractor

   backend = PdfPlumberExtractor()
   extractor = TextExtractor(backend)

   # Default chunking (4000 chars, 200 overlap)
   chunks = extractor.extract_chunked(Path("paper.pdf"))
   print(f"Created {len(chunks)} chunks")

   for i, chunk in enumerate(chunks):
       print(f"Chunk {i}: {len(chunk)} chars")
       print(f"  Preview: {chunk[:80]}...")

   # Custom chunk sizes
   # Smaller for embedding models
   small_chunks = extractor.extract_chunked(
       Path("paper.pdf"),
       chunk_size=512,
       overlap=50
   )

   # Larger for summarization
   large_chunks = extractor.extract_chunked(
       Path("paper.pdf"),
       chunk_size=8000,
       overlap=500
   )

   # Chunk specific pages only
   methods_chunks = extractor.extract_chunked(
       Path("paper.pdf"),
       chunk_size=4000,
       overlap=200,
       pages=[4, 5, 6, 7, 8]  # 0-indexed
   )

Table Extraction
~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from papercut.extractors.pdfplumber import PdfPlumberExtractor
   from papercut.core.tables import TableExtractor

   backend = PdfPlumberExtractor()
   extractor = TableExtractor(backend)

   # Extract all tables
   tables = extractor.extract(Path("paper.pdf"))
   print(f"Found {len(tables)} tables")

   for table in tables:
       print(f"\nTable on page {table.page}:")
       print(f"  Size: {table.rows} rows x {table.cols} columns")
       print(f"  Headers: {table.headers}")

       # Convert to different formats
       csv_data = table.to_csv()
       json_data = table.to_json()
       dict_rows = table.to_dict_rows()  # List of dicts with headers as keys

   # Extract from specific pages
   results_tables = extractor.extract(Path("paper.pdf"), pages=[10, 11, 12])

   # Get tables as CSV strings directly
   csv_tables = extractor.extract_as_csv(Path("paper.pdf"))
   for page_num, csv_string in csv_tables:
       print(f"Table on page {page_num}:")
       print(csv_string)

Working with Extracted Tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   import json
   from papercut.extractors.pdfplumber import PdfPlumberExtractor
   from papercut.core.tables import TableExtractor

   backend = PdfPlumberExtractor()
   extractor = TableExtractor(backend)
   tables = extractor.extract(Path("paper.pdf"))

   if tables:
       table = tables[0]

       # Save as CSV
       Path("table1.csv").write_text(table.to_csv())

       # Save as JSON
       Path("table1.json").write_text(table.to_json())

       # Work with data directly
       for row in table.data:
           print(row)

       # Convert to pandas DataFrame
       import pandas as pd
       df = pd.DataFrame(table.data[1:], columns=table.headers)
       print(df.describe())

Reference Extraction
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from papercut.extractors.pdfplumber import PdfPlumberExtractor
   from papercut.core.references import ReferenceExtractor

   backend = PdfPlumberExtractor()
   extractor = ReferenceExtractor(backend)

   # Extract references
   refs = extractor.extract(Path("paper.pdf"))
   print(f"Found {len(refs)} references")

   for ref in refs[:5]:  # First 5 references
       print(f"\nTitle: {ref.title}")
       print(f"Authors: {ref.authors}")
       print(f"Year: {ref.year}")
       if ref.doi:
           print(f"DOI: {ref.doi}")

   # Generate BibTeX
   bibtex_entries = [ref.to_bibtex() for ref in refs]
   bibtex_content = "\n\n".join(bibtex_entries)
   Path("references.bib").write_text(bibtex_content)

   # Generate JSON
   import json
   refs_data = [ref.to_dict() for ref in refs]
   Path("references.json").write_text(json.dumps(refs_data, indent=2))

Complete Extraction Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extract all content from a paper:

.. code-block:: python

   from pathlib import Path
   import json
   from papercut.extractors.pdfplumber import PdfPlumberExtractor
   from papercut.core.text import TextExtractor
   from papercut.core.tables import TableExtractor
   from papercut.core.references import ReferenceExtractor

   def extract_paper(pdf_path: Path, output_dir: Path):
       """Extract all content from a paper."""
       output_dir.mkdir(exist_ok=True)
       backend = PdfPlumberExtractor()

       # 1. Extract text
       text_extractor = TextExtractor(backend)
       text = text_extractor.extract(pdf_path)
       (output_dir / "text.txt").write_text(text)
       print(f"Extracted {len(text)} chars of text")

       # 2. Extract chunked text for LLM
       chunks = text_extractor.extract_chunked(pdf_path)
       chunks_data = [{"index": i, "text": c} for i, c in enumerate(chunks)]
       (output_dir / "chunks.json").write_text(json.dumps(chunks_data, indent=2))
       print(f"Created {len(chunks)} chunks")

       # 3. Extract tables
       table_extractor = TableExtractor(backend)
       tables = table_extractor.extract(pdf_path)
       tables_dir = output_dir / "tables"
       tables_dir.mkdir(exist_ok=True)
       for i, table in enumerate(tables):
           (tables_dir / f"table_{i+1}_page{table.page}.csv").write_text(table.to_csv())
       print(f"Extracted {len(tables)} tables")

       # 4. Extract references
       ref_extractor = ReferenceExtractor(backend)
       refs = ref_extractor.extract(pdf_path)
       bibtex = "\n\n".join(ref.to_bibtex() for ref in refs)
       (output_dir / "references.bib").write_text(bibtex)
       print(f"Extracted {len(refs)} references")

       return {
           "text_chars": len(text),
           "chunks": len(chunks),
           "tables": len(tables),
           "references": len(refs),
       }

   # Usage
   result = extract_paper(Path("paper.pdf"), Path("./output"))
   print(f"\nExtraction complete: {result}")

Batch Processing in Python
~~~~~~~~~~~~~~~~~~~~~~~~~~

Process multiple PDFs:

.. code-block:: python

   from pathlib import Path
   from papercut.extractors.pdfplumber import PdfPlumberExtractor
   from papercut.core.text import TextExtractor

   backend = PdfPlumberExtractor()
   extractor = TextExtractor(backend)

   papers_dir = Path("./papers")
   output_dir = Path("./extracted")
   output_dir.mkdir(exist_ok=True)

   results = []
   for pdf_path in papers_dir.glob("*.pdf"):
       try:
           text = extractor.extract(pdf_path)
           output_path = output_dir / f"{pdf_path.stem}.txt"
           output_path.write_text(text)

           results.append({
               "file": pdf_path.name,
               "chars": len(text),
               "status": "success"
           })
           print(f"[OK] {pdf_path.name}: {len(text)} chars")

       except Exception as e:
           results.append({
               "file": pdf_path.name,
               "status": "failed",
               "error": str(e)
           })
           print(f"[FAIL] {pdf_path.name}: {e}")

   # Summary
   success = sum(1 for r in results if r["status"] == "success")
   print(f"\nProcessed {success}/{len(results)} files")
