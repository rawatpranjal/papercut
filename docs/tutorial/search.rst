Searching for Papers
====================

Find academic papers on arXiv directly from the command line.

Basic Search
------------

Search for papers by keyword:

.. code-block:: bash

   papercutter search "transformer attention"

   papercutter search "machine learning optimization"

Results are returned as JSON:

.. code-block:: json

   {
     "query": "transformer attention",
     "source": "arxiv",
     "count": 3,
     "results": [
       {
         "id": "2209.15001v3",
         "title": "Dilated Neighborhood Attention Transformer",
         "authors": ["Ali Hassani", "Humphrey Shi"],
         "published": "2022-09-29",
         "abstract": "Transformers are quickly becoming one of the most heavily applied..."
       },
       {
         "id": "1809.04281v3",
         "title": "Music Transformer",
         "authors": ["Cheng-Zhi Anna Huang", "Ashish Vaswani", "..."],
         "published": "2018-09-12",
         "abstract": "Music relies heavily on repetition to build structure and meaning..."
       }
     ]
   }

Filtering Results
-----------------

Author Filter
~~~~~~~~~~~~~

Find papers by a specific author:

.. code-block:: bash

   papercutter search "attention" --author "Vaswani"

   papercutter search "neural networks" -a "Hinton"

Year Filter
~~~~~~~~~~~

Limit results to a specific publication year:

.. code-block:: bash

   papercutter search "large language models" --year 2023

Limit Results
~~~~~~~~~~~~~

Control the number of results:

.. code-block:: bash

   papercutter search "reinforcement learning" --limit 5

   papercutter search "diffusion models" -n 20

Combined Filters
~~~~~~~~~~~~~~~~

Combine multiple filters:

.. code-block:: bash

   papercutter search "diffusion models" \
     --author "Ho" \
     --year 2023 \
     --limit 10

Interactive Download
--------------------

Use ``--fetch`` to interactively select and download a paper:

.. code-block:: bash

   papercutter search "attention is all you need" --fetch -o ./papers/

This displays numbered results and prompts you to select one:

.. code-block:: console

   Found 5 result(s):

   1. Attention Is All You Need
      Ashish Vaswani, Noam Shazeer, Niki Parmar et al. (8 authors)
      arXiv:1706.03762 | 2017-06-12

   2. ...

   Enter number to download (or press Enter to skip): 1

   Downloading arXiv:1706.03762...
   Downloaded: ./papers/1706.03762.pdf

JSON Output
-----------

Search results are returned as JSON by default, ideal for scripting:

.. code-block:: bash

   papercutter search "transformer attention" --limit 3

Output:

.. code-block:: json

   {
     "query": "transformer attention",
     "source": "arxiv",
     "count": 3,
     "results": [
       {
         "id": "2209.15001v3",
         "title": "Dilated Neighborhood Attention Transformer",
         "authors": ["Ali Hassani", "Humphrey Shi"],
         "published": "2022-09-29",
         "abstract": "Transformers are quickly becoming one of the most heavily applied..."
       },
       {
         "id": "2309.01692v1",
         "title": "Mask-Attention-Free Transformer for 3D Instance Segmentation",
         "authors": ["Xin Lai", "Yuhui Yuan", "Ruihang Chu", "..."],
         "published": "2023-09-04",
         "abstract": "Recently, transformer-based methods have dominated 3D instance..."
       },
       {
         "id": "1809.04281v3",
         "title": "Music Transformer",
         "authors": ["Cheng-Zhi Anna Huang", "Ashish Vaswani", "..."],
         "published": "2018-09-12",
         "abstract": "Music relies heavily on repetition to build structure..."
       }
     ]
   }

Real-World Example: Building a Reading List
--------------------------------------------

Create a curated reading list on a research topic:

1. **Search for recent papers on a topic:**

   .. code-block:: bash

      papercutter search "chain of thought prompting" \
        --year 2023 \
        --limit 20 \
        --json > search_results.json

2. **Extract paper IDs and create a batch file:**

   .. code-block:: bash

      cat search_results.json | \
        jq -r '.results[].id | "arxiv:\(.)"' > reading_list.txt

3. **Preview the reading list:**

   .. code-block:: bash

      cat reading_list.txt
      # arxiv:2209.15001v3
      # arxiv:2309.01692v1
      # arxiv:1809.04281v3
      # ...

4. **Download all papers with batch fetch:**

   .. code-block:: bash

      papercutter fetch batch reading_list.txt \
        -o ./cot_papers/ \
        --metadata \
        --parallel

.. seealso::

   - :doc:`fetching` for downloading papers from search results
   - :doc:`follow` for downloading papers cited in references
