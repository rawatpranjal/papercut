"""Prompt templates for LLM-powered features."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PromptTemplate:
    """A reusable prompt template."""

    system: str
    user: str
    name: str = ""
    description: str = ""

    def format(self, **kwargs) -> tuple[str, str]:
        """Format the template with provided variables.

        Args:
            **kwargs: Variables to substitute in the template.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        return (
            self.system.format(**kwargs) if kwargs else self.system,
            self.user.format(**kwargs) if kwargs else self.user,
        )


# Base system prompt for academic paper analysis
ACADEMIC_SYSTEM = """You are an expert academic researcher and analyst.
You read papers carefully and extract information accurately.
You cite specific sections or quotes when possible.
You are honest about uncertainty - if something is unclear, say so.
You write in clear, concise academic prose."""


# Reading Group Summary Template
READING_GROUP = PromptTemplate(
    name="reading_group",
    description="1-page summary for reading group discussion",
    system=ACADEMIC_SYSTEM,
    user="""Summarize this academic paper for a reading group discussion.

Structure your summary with these sections:

## Research Question
What is the main question or problem the paper addresses?

## Methodology
- What is the identification strategy or approach?
- What data is used?
- What are the key assumptions?

## Main Findings
- What are the primary results?
- What is the magnitude/significance of effects?

## Contributions
- What is new or important about this paper?
- How does it advance the literature?

## Limitations & Discussion Points
- What are the weaknesses or caveats?
- What questions would you raise in discussion?

---

Paper text:
{text}

Provide a concise summary (~500-800 words) suitable for a 1-page handout.""",
)


# Meta-Analysis Extraction Template
META_ANALYSIS = PromptTemplate(
    name="meta_analysis",
    description="Structured extraction for meta-analysis",
    system=ACADEMIC_SYSTEM
    + """

When extracting data, be precise about:
- Effect sizes and their units
- Standard errors or confidence intervals
- Sample sizes and populations
- Identification strategies used

If a value is not clearly stated, return null rather than guessing.""",
    user="""Extract structured data from this paper for meta-analysis.

Return a JSON object with these fields:

{{
  "study_info": {{
    "title": "string",
    "authors": ["string"],
    "year": integer,
    "journal": "string or null"
  }},
  "methodology": {{
    "identification_strategy": "string (e.g., 'RCT', 'DiD', 'RDD', 'IV', 'OLS')",
    "estimator": "string or null",
    "controls": ["string"],
    "robustness_checks": ["string"]
  }},
  "data": {{
    "source": "string",
    "sample_size": integer or null,
    "time_period": "string or null",
    "geographic_scope": "string or null",
    "unit_of_analysis": "string"
  }},
  "results": {{
    "main_outcome": "string",
    "main_effect": number or null,
    "effect_unit": "string (e.g., 'percentage points', 'percent', 'dollars')",
    "standard_error": number or null,
    "confidence_interval": [number, number] or null,
    "p_value": number or null,
    "statistical_significance": boolean or null
  }},
  "heterogeneity": [
    {{
      "subgroup": "string",
      "effect": number or null,
      "se": number or null
    }}
  ]
}}

---

Paper text:
{text}

Extract all available information. Use null for missing values.""",
)


# Book Chapter Summary Template
BOOK_CHAPTER = PromptTemplate(
    name="book_chapter",
    description="Summary of a book chapter",
    system="""You are an expert at summarizing academic and technical books.
You identify key concepts, arguments, and takeaways.
You organize information hierarchically.
You note connections to other chapters or concepts when relevant.""",
    user="""Summarize this chapter from an academic/technical book.

Chapter: {chapter_name}

Structure your summary:

## Key Concepts
- List the main concepts or ideas introduced
- Define any important terms

## Main Arguments
- What are the chapter's central claims or points?
- What evidence or reasoning supports them?

## Practical Takeaways
- What should the reader remember or apply?

## Connections
- How does this connect to previous or upcoming material?
- What prerequisites are assumed?

---

Chapter text:
{text}

Provide a comprehensive but concise summary (~300-500 words).""",
)


# Book Synthesis Template
BOOK_SYNTHESIS = PromptTemplate(
    name="book_synthesis",
    description="Synthesize chapter summaries into book overview",
    system="""You are an expert at synthesizing information from multiple sources.
You identify overarching themes and connections.
You can distill large amounts of content into clear summaries.""",
    user="""Synthesize these chapter summaries into a cohesive book summary.

Book: {book_title}

Chapter summaries:
{chapter_summaries}

Create a synthesis that:

## Book Overview
- What is the book's main thesis or purpose?
- Who is the target audience?

## Key Themes
- What are the 3-5 major themes across chapters?

## Chapter Flow
- How do the chapters build on each other?
- What is the logical progression?

## Main Takeaways
- What are the most important insights from the book?

## Critical Assessment
- What are the book's strengths?
- What could be improved or is missing?

Provide a synthesis (~500-800 words).""",
)


# Simulation Code Generation Template
SIMULATION = PromptTemplate(
    name="simulation",
    description="Generate simulation code from paper model",
    system="""You are an expert at translating theoretical economic/statistical models into code.
You write clean, documented, runnable code.
You include parameter definitions and comments explaining the model.
You provide both Python and R versions when requested.""",
    user="""Extract the theoretical model from this paper and generate simulation code.

Target language: {language}

Your code should:
1. Define all model parameters with sensible defaults
2. Implement the core model logic
3. Run a basic simulation demonstrating the model
4. Include comments explaining each part
5. Be runnable as-is (no missing imports or undefined variables)

---

Paper text:
{text}

---

Generate {language} code that simulates the paper's main model.
If multiple models exist, focus on the primary/simplest one.
Include a docstring explaining what the model represents.""",
)


# Get template by name
TEMPLATES = {
    "reading_group": READING_GROUP,
    "meta_analysis": META_ANALYSIS,
    "book_chapter": BOOK_CHAPTER,
    "book_synthesis": BOOK_SYNTHESIS,
    "simulation": SIMULATION,
}


def get_template(name: str) -> Optional[PromptTemplate]:
    """Get a prompt template by name.

    Args:
        name: Template name.

    Returns:
        PromptTemplate or None if not found.
    """
    return TEMPLATES.get(name)


def list_templates() -> list[str]:
    """List available template names.

    Returns:
        List of template names.
    """
    return list(TEMPLATES.keys())
