LLM Features
============

AI-powered analysis for papers and books.

Setup
-----

Install with LLM support:

.. code-block:: bash

   pip install papercut[llm]

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
   papercut summarize paper.pdf

   # Focus on specific aspects
   papercut summarize paper.pdf --focus methods
   papercut summarize paper.pdf --focus results
   papercut summarize paper.pdf --focus contributions

   # Adjust length
   papercut summarize paper.pdf --length short
   papercut summarize paper.pdf --length long

Reports
-------

Generate structured reports for different audiences:

.. code-block:: bash

   # Reading group presentation
   papercut report paper.pdf --template reading-group

   # Referee review
   papercut report paper.pdf --template referee

   # Meta-analysis notes
   papercut report paper.pdf --template meta

   # Executive summary
   papercut report paper.pdf --template executive

Study Aids
----------

Generate study materials from book chapters:

.. code-block:: bash

   # Chapter summary
   papercut study book.pdf --chapter 5

   # Key concepts
   papercut study book.pdf --chapter 5 --mode concepts

   # Practice quiz
   papercut study book.pdf --chapter 5 --mode quiz

   # Flashcards
   papercut study book.pdf --chapter 5 --mode flashcards

Python API
----------

Use the intelligence module directly in Python:

Summarizer
^^^^^^^^^^

.. code-block:: python

   from pathlib import Path
   from papercut.intelligence import Summarizer

   summarizer = Summarizer()

   # Check availability
   if not summarizer.is_available():
       print("LLM not configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")
   else:
       # Generate summary
       summary = summarizer.summarize(
           Path("paper.pdf"),
           focus="methods",  # Optional: methods, results, contributions
           length="default",  # short, default, long
       )

       print(summary.content)
       print(f"Tokens used: {summary.input_tokens} in, {summary.output_tokens} out")

Report Generator
^^^^^^^^^^^^^^^^

.. code-block:: python

   from pathlib import Path
   from papercut.intelligence import ReportGenerator

   generator = ReportGenerator()

   # List available templates
   print(generator.list_templates())
   # ['reading-group', 'referee', 'meta', 'executive']

   # Generate a report
   report = generator.generate(
       Path("paper.pdf"),
       template="referee",
   )

   print(report.content)
   print(f"Model: {report.model}")

   # Use custom template
   report = generator.generate(
       Path("paper.pdf"),
       custom_template=Path("my_template.txt"),
   )

Study Aid
^^^^^^^^^

.. code-block:: python

   from pathlib import Path
   from papercut.intelligence import StudyAid

   study = StudyAid()

   # List available modes
   print(study.list_modes())
   # ['summary', 'concepts', 'quiz', 'flashcards']

   # Generate flashcards for chapter 3
   material = study.generate(
       Path("book.pdf"),
       mode="flashcards",
       chapter=3,
   )

   print(material.content)

   # Or specify pages directly
   material = study.generate(
       Path("book.pdf"),
       mode="quiz",
       pages=[50, 51, 52, 53, 54],  # 0-indexed
   )

Token Usage
^^^^^^^^^^^

All intelligence classes return token usage information:

.. code-block:: python

   summary = summarizer.summarize(Path("paper.pdf"))

   # Access token counts
   print(f"Input tokens: {summary.input_tokens}")
   print(f"Output tokens: {summary.output_tokens}")
   print(f"Model used: {summary.model}")

   # Convert to dictionary for JSON serialization
   data = summary.to_dict()
