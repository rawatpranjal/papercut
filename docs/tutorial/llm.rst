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

Complete Workflows
------------------

These examples show how to combine Papercut features for common research tasks.

Paper Analysis Pipeline
^^^^^^^^^^^^^^^^^^^^^^^

Fetch, extract, and analyze a paper:

.. code-block:: python

   from pathlib import Path
   from papercut.fetchers.arxiv import ArxivFetcher
   from papercut.intelligence import Summarizer, ReportGenerator
   from papercut.core.references import ReferenceExtractor
   from papercut.extractors.pdfplumber import PdfPlumberExtractor

   def analyze_paper(arxiv_id: str, output_dir: Path):
       """Complete analysis of an arXiv paper."""
       output_dir.mkdir(exist_ok=True)

       # 1. Fetch the paper
       fetcher = ArxivFetcher()
       doc = fetcher.fetch(arxiv_id, output_dir)
       print(f"Fetched: {doc.title}")

       # 2. Generate summary
       summarizer = Summarizer()
       if summarizer.is_available():
           summary = summarizer.summarize(doc.path, focus="contributions")
           (output_dir / "summary.txt").write_text(summary.content)
           print(f"Summary: {len(summary.content)} chars")

       # 3. Generate referee report
       reporter = ReportGenerator()
       if reporter.is_available():
           report = reporter.generate(doc.path, template="referee")
           (output_dir / "referee_report.txt").write_text(report.content)
           print(f"Report: {len(report.content)} chars")

       # 4. Extract references
       backend = PdfPlumberExtractor()
       ref_extractor = ReferenceExtractor(backend)
       refs = ref_extractor.extract(doc.path)
       bibtex = "\n\n".join(ref.to_bibtex() for ref in refs)
       (output_dir / "references.bib").write_text(bibtex)
       print(f"References: {len(refs)} entries")

       return {
           "title": doc.title,
           "path": str(doc.path),
           "references": len(refs),
       }

   # Usage
   result = analyze_paper("2301.00001", Path("./analysis"))
   print(f"Analysis complete: {result}")

Batch Paper Summarization
^^^^^^^^^^^^^^^^^^^^^^^^^

Summarize multiple papers with cost tracking:

.. code-block:: python

   from pathlib import Path
   from papercut.intelligence import Summarizer

   summarizer = Summarizer()

   if not summarizer.is_available():
       print("LLM not configured")
       exit(1)

   papers = list(Path("./papers").glob("*.pdf"))
   print(f"Processing {len(papers)} papers...")

   results = []
   total_input_tokens = 0
   total_output_tokens = 0

   for paper in papers:
       try:
           summary = summarizer.summarize(paper, length="short")

           results.append({
               "file": paper.name,
               "summary": summary.content,
               "input_tokens": summary.input_tokens,
               "output_tokens": summary.output_tokens,
           })

           total_input_tokens += summary.input_tokens
           total_output_tokens += summary.output_tokens

           print(f"[OK] {paper.name}: {summary.input_tokens}+{summary.output_tokens} tokens")

       except Exception as e:
           results.append({
               "file": paper.name,
               "error": str(e),
           })
           print(f"[FAIL] {paper.name}: {e}")

   # Summary
   success = sum(1 for r in results if "summary" in r)
   print(f"\nProcessed: {success}/{len(papers)}")
   print(f"Total tokens: {total_input_tokens} input, {total_output_tokens} output")

   # Estimate cost (example for Claude)
   input_cost = total_input_tokens * 0.003 / 1000  # $3/M input
   output_cost = total_output_tokens * 0.015 / 1000  # $15/M output
   print(f"Estimated cost: ${input_cost + output_cost:.4f}")

Reading Group Preparation
^^^^^^^^^^^^^^^^^^^^^^^^^

Generate materials for a reading group discussion:

.. code-block:: python

   from pathlib import Path
   from papercut.intelligence import Summarizer, ReportGenerator
   from papercut.index import DocumentIndexer

   def prepare_reading_group(pdf_path: Path, output_dir: Path):
       """Prepare materials for reading group."""
       output_dir.mkdir(exist_ok=True)

       # 1. Index the document
       indexer = DocumentIndexer()
       doc_index = indexer.index(pdf_path)
       print(f"Indexed: {len(doc_index.sections)} sections")

       # 2. Generate overview summary
       summarizer = Summarizer()
       overview = summarizer.summarize(pdf_path, length="short")
       (output_dir / "overview.txt").write_text(overview.content)

       # 3. Generate reading group report
       reporter = ReportGenerator()
       report = reporter.generate(pdf_path, template="reading-group")
       (output_dir / "discussion_guide.txt").write_text(report.content)

       # 4. Generate section-by-section notes
       notes = ["# Section Notes\n"]
       for section in doc_index.sections:
           notes.append(f"## {section.title} (pages {section.pages[0]}-{section.pages[1]})")
           notes.append(f"- Key area for discussion\n")

       (output_dir / "section_notes.md").write_text("\n".join(notes))

       print(f"Materials saved to {output_dir}")

   # Usage
   prepare_reading_group(Path("paper.pdf"), Path("./reading_group"))

Study Session Workflow
^^^^^^^^^^^^^^^^^^^^^^

Create study materials from a textbook chapter:

.. code-block:: python

   from pathlib import Path
   from papercut.intelligence import StudyAid
   from papercut.books.splitter import ChapterSplitter

   def create_study_session(book_path: Path, chapter_num: int, output_dir: Path):
       """Create comprehensive study materials for a chapter."""
       output_dir.mkdir(exist_ok=True)
       study = StudyAid()

       # 1. Get chapter info
       splitter = ChapterSplitter()
       chapters = splitter.detect_chapters(book_path)

       if chapter_num > len(chapters):
           print(f"Only {len(chapters)} chapters found")
           return

       chapter = chapters[chapter_num - 1]
       print(f"Chapter {chapter_num}: {chapter.title}")
       print(f"Pages: {chapter.start_page + 1} to {chapter.end_page}")

       # 2. Generate summary
       summary = study.generate(book_path, mode="summary", chapter=chapter_num)
       (output_dir / "summary.txt").write_text(summary.content)
       print("Created: summary.txt")

       # 3. Generate key concepts
       concepts = study.generate(book_path, mode="concepts", chapter=chapter_num)
       (output_dir / "concepts.txt").write_text(concepts.content)
       print("Created: concepts.txt")

       # 4. Generate flashcards
       flashcards = study.generate(book_path, mode="flashcards", chapter=chapter_num)
       (output_dir / "flashcards.txt").write_text(flashcards.content)
       print("Created: flashcards.txt")

       # 5. Generate practice quiz
       quiz = study.generate(book_path, mode="quiz", chapter=chapter_num)
       (output_dir / "quiz.txt").write_text(quiz.content)
       print("Created: quiz.txt")

       print(f"\nStudy materials saved to {output_dir}")

   # Usage
   create_study_session(Path("textbook.pdf"), chapter_num=5, Path("./study"))

Model Configuration
-------------------

Papercut supports multiple LLM providers through LiteLLM.

Using Different Providers
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Anthropic Claude (default if ANTHROPIC_API_KEY is set)
   export ANTHROPIC_API_KEY=sk-ant-...

   # OpenAI
   export OPENAI_API_KEY=sk-...

   # Azure OpenAI
   export AZURE_API_KEY=...
   export AZURE_API_BASE=https://your-resource.openai.azure.com/

Selecting a Model
^^^^^^^^^^^^^^^^^

Override the default model via environment variable:

.. code-block:: bash

   # Use a specific Claude model
   export PAPERCUT_MODEL=claude-3-opus-20240229

   # Use GPT-4
   export PAPERCUT_MODEL=gpt-4-turbo

   # Use a smaller/faster model
   export PAPERCUT_MODEL=claude-3-haiku-20240307

Configuration File
^^^^^^^^^^^^^^^^^^

Create ``~/.papercut/config.yaml`` for persistent settings:

.. code-block:: yaml

   # LLM settings
   llm:
     model: claude-3-sonnet-20240229
     max_tokens: 4096
     temperature: 0.7

   # API keys (can also use environment variables)
   anthropic_api_key: sk-ant-...

   # Output preferences
   output:
     default_dir: ~/papers
     format: json

Tips
----

1. **Token limits**: Long papers may be truncated. Use ``--focus`` to target specific sections.

2. **Cost awareness**: Track token usage when processing many papers.

3. **Model selection**: Use faster/cheaper models (Haiku, GPT-3.5) for drafts, better models (Opus, GPT-4) for final outputs.

4. **Caching**: LLM results are not cached. Save outputs to files for reuse.

5. **Error handling**: Always check ``is_available()`` before using LLM features.

6. **Custom templates**: Create your own report templates for specialized use cases.
