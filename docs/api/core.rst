Core
====

Content extraction from PDFs.

Text
----

.. autoclass:: papercutter.core.text.TextExtractor
   :members:

Tables
------

.. autoclass:: papercutter.core.tables.ExtractedTable
   :members:

.. autoclass:: papercutter.core.tables.TableExtractor
   :members:

References
----------

.. autoclass:: papercutter.core.references.Reference
   :members:

.. autoclass:: papercutter.core.references.ReferenceExtractor
   :members:

Figures
-------

.. autoclass:: papercutter.core.figures.ExtractedFigure
   :members:

.. autoclass:: papercutter.core.figures.FigureExtractor
   :members:

Equations
---------

Equation detection and extraction with optional LaTeX conversion.
Requires PyMuPDF (``pip install pymupdf``).

.. autoclass:: papercutter.core.equations.EquationType
   :members:
   :undoc-members:

.. autoclass:: papercutter.core.equations.EquationBbox
   :members:
   :undoc-members:

.. autoclass:: papercutter.core.equations.LaTeXConversion
   :members:
   :undoc-members:

.. autoclass:: papercutter.core.equations.ExtractedEquation
   :members:
   :undoc-members:

.. autoclass:: papercutter.core.equations.EquationExtractionResult
   :members:
   :undoc-members:

.. autoclass:: papercutter.core.equations.EquationExtractor
   :members:
   :undoc-members:
