Papercutter
===========

Turn your PDF collection into a dataset you can actually use.

.. code-block:: bash

   pip install papercutter[full]

----

Pipeline
--------

.. grid:: 2 2 2 2
   :gutter: 3

   .. grid-item-card:: 1. Ingest
      :link: quickstart.html#ingest

      ``papercutter ingest ./pdfs/``

      Convert PDFs to Markdown. Extract tables and figures.

   .. grid-item-card:: 2. Configure
      :link: quickstart.html#configure

      ``papercutter configure``

      Generate ``columns.yaml`` schema from paper abstracts.

   .. grid-item-card:: 3. Extract
      :link: quickstart.html#extract

      ``papercutter extract``

      Extract structured data from each paper using LLM.

   .. grid-item-card:: 4. Report
      :link: quickstart.html#report

      ``papercutter report``

      Output ``matrix.csv`` and ``review.pdf``.

----

Use Cases
---------

- **Systematic reviews** - Extract study characteristics from 50+ papers
- **Meta-analysis** - Pull effect sizes and standard errors into a dataset
- **Literature surveys** - Summarize key findings across a research area
- **Book notes** - Distill handbooks into chapter-by-chapter summaries

----

Example
-------

.. code-block:: bash

   export OPENAI_API_KEY="sk-..."

   papercutter ingest ./papers/
   papercutter configure
   papercutter extract
   papercutter report

Outputs ``matrix.csv`` (for R/Stata) and ``review.pdf`` (LaTeX report).

----

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   installation
   quickstart
   tutorial
   reference
