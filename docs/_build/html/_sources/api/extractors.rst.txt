Extractors
==========

PDF content extraction backends.

Protocol
--------

.. autoclass:: papercutter.extractors.base.Extractor
   :members:

Backends
--------

**PdfPlumber** (default)

.. autoclass:: papercutter.extractors.pdfplumber.PdfPlumberExtractor
   :members:

**PyMuPDF** (fast) - ``pip install papercutter[fast]``

Set via: ``PAPERCUTTER_EXTRACTION__BACKEND=pymupdf``
