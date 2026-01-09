Extracting Equations
====================

Papercutter can detect and extract mathematical equations from PDFs,
saving them as high-resolution PNG images with optional LaTeX conversion.

Setup
-----

Equation extraction requires PyMuPDF:

.. code-block:: bash

   pip install pymupdf

For LaTeX conversion, install one of the converter backends:

.. code-block:: bash

   # Nougat (free, local, ~1GB model download on first use)
   pip install nougat-ocr

   # pix2tex (free, local, lightweight)
   pip install pix2tex

   # MathPix (paid API, highest accuracy)
   # Set environment variables:
   export PAPERCUTTER_MATHPIX_APP_ID="your-app-id"
   export PAPERCUTTER_MATHPIX_APP_KEY="your-app-key"

Basic Usage
-----------

Extract all equations from a PDF:

.. code-block:: bash

   papercutter equations textbook.pdf

   papercutter equations textbook.pdf -o ./equations/

By default, equations are cached and Nougat is used for LaTeX conversion.

Page Selection
~~~~~~~~~~~~~~

Extract equations from specific pages:

.. code-block:: bash

   papercutter equations textbook.pdf --pages 40-50

   papercutter equations textbook.pdf -p 1-20

LaTeX Conversion
----------------

Conversion Methods
~~~~~~~~~~~~~~~~~~

Papercutter supports three LaTeX conversion backends:

**Nougat** (default):

.. code-block:: bash

   papercutter equations paper.pdf --method nougat

- Free, runs locally
- Downloads ~1GB model on first run
- Good accuracy for complex equations

**pix2tex**:

.. code-block:: bash

   papercutter equations paper.pdf --method pix2tex

- Free, runs locally
- Lightweight (~50MB)
- Fast, good for simple equations

**MathPix**:

.. code-block:: bash

   papercutter equations paper.pdf --method mathpix

- Paid API (~95% accuracy)
- Requires API credentials
- Best for production use

Skip LaTeX Conversion
~~~~~~~~~~~~~~~~~~~~~

For faster extraction (images only):

.. code-block:: bash

   papercutter equations paper.pdf --no-latex

   # Or explicitly set method to none
   papercutter equations paper.pdf --method none

Confidence Thresholds
---------------------

Filter low-confidence conversions:

.. code-block:: bash

   papercutter equations paper.pdf --min-confidence 0.8

The ``--verify`` flag shows warnings for low-confidence results:

.. code-block:: bash

   papercutter equations paper.pdf --min-confidence 0.7 --verify

Example output:

.. code-block:: console

   Warning: 3 equation(s) with low confidence:
     - Equation #5 (page 12): 65.2% confidence
     - Equation #8 (page 15): 58.1% confidence
     - Equation #12 (page 22): 71.3% confidence

Image Quality
-------------

Control the DPI for equation images (72-600):

.. code-block:: bash

   # Higher DPI for better quality (larger files)
   papercutter equations paper.pdf --dpi 600

   # Lower DPI for smaller files
   papercutter equations paper.pdf --dpi 150

Inline vs Display Equations
---------------------------

By default, both inline and display equations are detected. To extract only
display (block) equations:

.. code-block:: bash

   papercutter equations paper.pdf --no-detect-inline

Output Format
-------------

JSON output includes equation metadata:

.. code-block:: bash

   papercutter equations paper.pdf --no-latex --json

Example from "Attention Is All You Need" (arXiv:1706.03762):

.. code-block:: json

   {
     "success": true,
     "file": "Vaswani_2017_attention_is_all_you_need.pdf",
     "count": 17,
     "pages_processed": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
     "method": null,
     "low_confidence_count": 0,
     "equations": [
       {
         "id": 1,
         "page": 2,
         "type": "display",
         "bbox": {"x0": 238.75, "y0": 679.49, "x1": 444.19, "y1": 700.36},
         "format": "png",
         "image_path": "~/.cache/papercutter/.../equations/eq_1.png",
         "context": "...Most competitive neural sequence transduction models..."
       },
       {
         "id": 3,
         "page": 4,
         "type": "display",
         "bbox": {"x0": 209.08, "y0": 572.48, "x1": 341.58, "y1": 593.35},
         "format": "png",
         "image_path": "~/.cache/papercutter/.../equations/eq_3.png",
         "context": "...efficient in practice, since it can be implemented..."
       }
     ]
   }

Extract Single Equation
-----------------------

Retrieve a specific equation by ID:

.. code-block:: bash

   papercutter equation paper.pdf --id 3

   papercutter equation paper.pdf --id 3 -o equation_3.png

The equation command checks the cache first for faster access.

Real-World Example: Extracting Equations from "Attention Is All You Need"
--------------------------------------------------------------------------

Extract equations from the famous Transformer paper (arXiv:1706.03762):

1. **Fetch the paper:**

   .. code-block:: bash

      papercutter fetch arxiv 1706.03762 -o ./papers/

2. **Extract equations (images only, fast):**

   .. code-block:: bash

      papercutter equations ./papers/Vaswani_2017_attention_is_all_you_need.pdf \
        --no-latex \
        -o ./equations/ \
        --json > equations.json

   Output shows 17 equations detected across 15 pages.

3. **View extracted equations:**

   .. code-block:: bash

      ls ./equations/
      # eq_1.png  eq_2.png  eq_3.png  eq_4.png  ...

4. **Filter equations by page using jq:**

   .. code-block:: bash

      cat equations.json | jq '.equations[] | select(.page == 4) | {id, page, type}'
      # {"id": 3, "page": 4, "type": "display"}
      # {"id": 4, "page": 4, "type": "display"}

5. **Extract a single equation:**

   .. code-block:: bash

      papercutter equation ./papers/Vaswani_2017_attention_is_all_you_need.pdf \
        --id 3 -o attention_formula.png

.. seealso::

   - :doc:`../api/core` for the ``EquationExtractor`` Python API
   - :doc:`../api/converters` for LaTeX converter details
