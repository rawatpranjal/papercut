Converters
==========

LaTeX conversion backends for equation images.

Papercutter supports converting extracted equation images to LaTeX using
multiple backends. Each converter implements the same interface but uses
different underlying technology.

Base Converter
--------------

.. autoclass:: papercutter.converters.base.BaseConverter
   :members:
   :undoc-members:

Nougat Converter
----------------

Neural-based LaTeX conversion using Meta's Nougat model. Good accuracy for
complex equations but requires a ~1GB model download on first use.

.. code-block:: bash

   pip install nougat-ocr

.. autoclass:: papercutter.converters.nougat.NougatConverter
   :members:
   :show-inheritance:

pix2tex Converter
-----------------

Lightweight image-to-LaTeX conversion. Fast and suitable for simple to
moderately complex equations.

.. code-block:: bash

   pip install pix2tex

.. autoclass:: papercutter.converters.pix2tex.Pix2TexConverter
   :members:
   :show-inheritance:

MathPix Converter
-----------------

High-accuracy LaTeX conversion using the MathPix API. Requires API credentials
but provides the best results for production use.

Configure with environment variables:

.. code-block:: bash

   export PAPERCUTTER_MATHPIX_APP_ID="your-app-id"
   export PAPERCUTTER_MATHPIX_APP_KEY="your-app-key"

.. autoclass:: papercutter.converters.mathpix.MathPixConverter
   :members:
   :show-inheritance:

Choosing a Converter
--------------------

+-----------+-------------+-----------+---------------+-------------------+
| Converter | Accuracy    | Speed     | Size          | Cost              |
+===========+=============+===========+===============+===================+
| nougat    | High        | Medium    | ~1GB          | Free (local)      |
+-----------+-------------+-----------+---------------+-------------------+
| pix2tex   | Medium      | Fast      | ~50MB         | Free (local)      |
+-----------+-------------+-----------+---------------+-------------------+
| mathpix   | Very High   | Fast      | None (API)    | Paid API          |
+-----------+-------------+-----------+---------------+-------------------+

.. seealso::

   :doc:`../tutorial/equations` for CLI usage of equation extraction with LaTeX conversion.
