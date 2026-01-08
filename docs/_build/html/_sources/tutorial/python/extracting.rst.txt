Extracting Content
==================

Use extractors programmatically for full control and integration with other tools.

Setting Up Extractors
---------------------

.. code-block:: python

   from pathlib import Path
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.text import TextExtractor
   from papercutter.core.tables import TableExtractor
   from papercutter.core.references import ReferenceExtractor

   # Initialize the backend (pdfplumber is the default)
   backend = PdfPlumberExtractor()

   # Create specialized extractors
   text_extractor = TextExtractor(backend)
   table_extractor = TableExtractor(backend)
   ref_extractor = ReferenceExtractor(backend)

Text Extraction
---------------

.. code-block:: python

   from pathlib import Path
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.text import TextExtractor

   backend = PdfPlumberExtractor()
   extractor = TextExtractor(backend)

   # Extract all text
   text = extractor.extract(Path("paper.pdf"))
   print(f"Extracted {len(text)} characters")

   # Extract from specific pages (0-indexed)
   intro_text = extractor.extract(Path("paper.pdf"), pages=[0, 1, 2])
   print(f"Introduction: {intro_text[:200]}...")

Chunking for LLMs
-----------------

The chunker is sentence-aware and avoids breaking mid-sentence:

.. code-block:: python

   from pathlib import Path
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.text import TextExtractor

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
----------------

.. code-block:: python

   from pathlib import Path
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.tables import TableExtractor

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
-----------------------------

.. code-block:: python

   from pathlib import Path
   import json
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.tables import TableExtractor

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
--------------------

.. code-block:: python

   from pathlib import Path
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.references import ReferenceExtractor

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
----------------------------

Extract all content from a paper:

.. code-block:: python

   from pathlib import Path
   import json
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.text import TextExtractor
   from papercutter.core.tables import TableExtractor
   from papercutter.core.references import ReferenceExtractor

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

Batch Processing
----------------

Process multiple PDFs:

.. code-block:: python

   from pathlib import Path
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.text import TextExtractor

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

Real-World Example: Extracting from Thompson (2022)
----------------------------------------------------

This example demonstrates extraction from an actual paper (``Thompson_2022_nftrig.pdf``):

.. code-block:: python

   from pathlib import Path
   from papercutter.extractors.pdfplumber import PdfPlumberExtractor
   from papercutter.core.text import TextExtractor
   from papercutter.core.references import ReferenceExtractor

   # Set up extractors
   pdf_path = Path("Thompson_2022_nftrig.pdf")
   backend = PdfPlumberExtractor()

   # Extract text
   text_ext = TextExtractor(backend)
   text = text_ext.extract(pdf_path)
   print(f"Total characters: {len(text):,}")

Actual output:

.. code-block:: text

   Total characters: 50,216

Chunking for LLM Processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   chunks = text_ext.extract_chunked(pdf_path, chunk_size=2000, overlap=200)
   print(f"Total chunks: {len(chunks)}")
   for i, chunk in enumerate(chunks[:3]):
       print(f"Chunk {i}: {len(chunk)} chars")

Actual output:

.. code-block:: text

   Total chunks: 29
   Chunk 0: 1996 chars
   Chunk 1: 1925 chars
   Chunk 2: 2000 chars

Extracting References
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   ref_ext = ReferenceExtractor(backend)
   refs = ref_ext.extract(pdf_path)
   print(f"Found {len(refs)} references")

   for ref in refs[:3]:
       authors = ref.authors[0] if ref.authors else "Unknown"
       title = ref.title[:50] if ref.title else "Untitled"
       print(f"  - {authors} ({ref.year}): {title}...")

Actual output:

.. code-block:: text

   Found 35 references
     - Rana MAmir Latif (2020): AremixIDE:smart contract-basedframeworkfo...
     - Mohsen Attaranand Angappa Gunasekaran (2019): BlockchainforGaming.InApplicationsofBlockchainTech...
     - Rocsana Bucea-Manea-Toniş (2021): BlockchainTechnologyEnhancesSustainableHigherEduca...

Complete Pipeline with Output Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import json
   from pathlib import Path

   # Create output directory
   output = Path("./extracted")
   output.mkdir(exist_ok=True)

   # 1. Save full text
   (output / "full_text.txt").write_text(text)

   # 2. Create LLM-ready chunks
   chunks_data = [{"index": i, "chars": len(c), "preview": c[:100]} for i, c in enumerate(chunks)]
   (output / "chunks.json").write_text(json.dumps(chunks_data, indent=2))
   print(f"Created {len(chunks)} chunks for LLM processing")

   # 3. Export references as BibTeX
   bibtex = "\n\n".join(ref.to_bibtex() for ref in refs)
   (output / "references.bib").write_text(bibtex)

   print(f"\nOutput structure:")
   for f in sorted(output.rglob("*")):
       if f.is_file():
           print(f"  {f.relative_to(output)}: {f.stat().st_size:,} bytes")

Actual output:

.. code-block:: text

   Created 29 chunks for LLM processing

   Output structure:
     chunks.json: 10,234 bytes
     full_text.txt: 50,216 bytes
     references.bib: 7,845 bytes
