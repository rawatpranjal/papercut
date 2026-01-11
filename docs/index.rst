Papercutter
===========

Extract structured data from academic papers.

.. code-block:: bash

   pip install papercutter[full]

.. grid:: 2 2 2 2
   :gutter: 2

   .. grid-item-card:: 1. Ingest
      :class-card: sd-bg-primary sd-text-white

      ``papercutter ingest ./pdfs/``

      PDF -> Markdown + Tables (Docling)

   .. grid-item-card:: 2. Configure
      :class-card: sd-bg-secondary sd-text-white

      ``papercutter configure``

      Generate columns.yaml schema

   .. grid-item-card:: 3. Grind
      :class-card: sd-bg-info sd-text-white

      ``papercutter grind``

      Extract data via LLM

   .. grid-item-card:: 4. Report
      :class-card: sd-bg-success sd-text-white

      ``papercutter report [-c]``

      Generate matrix.csv + review.pdf

.. toctree::
   :hidden:

   installation
   quickstart
   tutorial
   reference
