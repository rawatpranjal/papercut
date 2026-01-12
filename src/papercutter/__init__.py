"""Papercutter: Extract structured data from academic papers.

The Pipeline:
    papercutter ingest     # Digitize PDFs with Docling
    papercutter configure  # Generate extraction schema
    papercutter extract    # Extract data fields with LLM
    papercutter report     # Generate matrix.csv + review.pdf
"""

__version__ = "3.1.0"

__all__ = ["__version__"]
