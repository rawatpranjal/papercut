"""Papercutter: PDF to Data Factory.

Extract structured data from academic papers into CSV and PDF reports.

The Razor Pipeline:
    papercutter ingest     # Digitize PDFs with Docling
    papercutter configure  # Generate extraction schema
    papercutter grind      # Extract data fields with LLM
    papercutter report     # Generate matrix.csv + review.pdf
"""

__version__ = "3.0.0"

__all__ = ["__version__"]
