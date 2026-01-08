LLM Features
============

AI-powered analysis for papers and books.

Setup
-----

Install with LLM support:

.. code-block:: bash

   pip install papercutter[llm]

Set your API key:

.. code-block:: bash

   export OPENAI_API_KEY=sk-...
   # or
   export ANTHROPIC_API_KEY=sk-...

Summarizing Papers
------------------

Generate summaries with customizable focus and length:

.. code-block:: bash

   # Default summary
   papercutter summarize paper.pdf

   # Focus on specific aspects
   papercutter summarize paper.pdf --focus methods
   papercutter summarize paper.pdf --focus results
   papercutter summarize paper.pdf --focus contributions

   # Adjust length
   papercutter summarize paper.pdf --length short
   papercutter summarize paper.pdf --length long

Reports
-------

Generate structured reports for different audiences:

.. code-block:: bash

   # Reading group presentation
   papercutter report paper.pdf --template reading-group

   # Referee review
   papercutter report paper.pdf --template referee

   # Meta-analysis notes
   papercutter report paper.pdf --template meta

   # Executive summary
   papercutter report paper.pdf --template executive

Study Aids
----------

Generate study materials from book chapters:

.. code-block:: bash

   # Chapter summary
   papercutter study book.pdf --chapter 5

   # Key concepts
   papercutter study book.pdf --chapter 5 --mode concepts

   # Practice quiz
   papercutter study book.pdf --chapter 5 --mode quiz

   # Flashcards
   papercutter study book.pdf --chapter 5 --mode flashcards

Tips
----

1. **Token limits**: Long papers may be truncated. Use ``--focus`` to target specific sections.

2. **Model selection**: Configure via ``PAPERCUTTER_MODEL`` environment variable.

3. **Cost awareness**: LLM calls consume tokens. Track usage for budgeting.

.. seealso::

   :doc:`python/workflows` for Python API examples including batch processing, complete pipelines, and model configuration.

Case Study: Flash Report from a Real Paper
------------------------------------------

The following sequence shows actual commands and representative output using ``Thompson_2022_nftrig.pdf`` (included in the repository’s ``/`` root, but any PDF works):

1. **Summarize with a methodology focus to brief collaborators:**

   .. code-block:: bash

      papercutter summarize Thompson_2022_nftrig.pdf --focus methodology --length short \\
        -o sums/methodology.json

   Sample output (truncated):

   .. code-block:: json

      {
        "summary": "The paper studies how NFTs create coordinated triggers for community events...",
        "focus": "methodology",
        "model": "claude-sonnet-4-20250514",
        "tokens": {"input": 9021, "output": 622}
      }

2. **Generate a referee-style report to simulate peer-review comments:**

   .. code-block:: bash

      papercutter report Thompson_2022_nftrig.pdf --template referee \\
        -o reports/nft_referee.md

   Snippet of the Markdown report:

   .. code-block:: markdown

      ## Main Contributions
      - Demonstrates how NFT drops act as external shocks to online communities.
      - Provides a natural experiment for studying retention mechanics.

      ## Weaknesses
      - Limited evidence on long-term platform engagement.
      - Needs clarity on how synthetic controls were constructed.

3. **Produce flashcards for teaching/discussion prep:**

   .. code-block:: bash

      papercutter study Thompson_2022_nftrig.pdf --mode flashcards \\
        -o study/nft_flashcards.md

   Example card:

   .. code-block:: text

      ---
      **Front**: What is the main research question?
      **Back**: Whether blockchain-triggered scarcity campaigns can activate dormant audiences.
      ---

Together these commands deliver an end-to-end “real world” flow: ingest a PDF, capture a shareable summary, mock a reviewer’s perspective, and create teaching aids in under five minutes.
