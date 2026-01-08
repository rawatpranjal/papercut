"""Prompt templates for LLM-powered features."""

# System prompts
SYSTEM_SUMMARIZE = """You are a research assistant specializing in academic paper analysis.
Your task is to provide clear, accurate summaries of academic papers.
Focus on key findings, methodology, and implications.
Be concise but thorough. Use technical language appropriately."""

SYSTEM_REPORT = """You are a research assistant helping to generate structured reports about academic papers.
Follow the provided template structure exactly.
Be analytical and critical in your assessment.
Support claims with specific details from the paper."""

SYSTEM_STUDY = """You are an educational assistant helping students understand academic content.
Explain concepts clearly and provide helpful study materials.
Adapt your explanations to be accessible while maintaining accuracy."""

# Prompt templates
SUMMARIZE_DEFAULT = """Summarize the following academic paper:

{content}

Provide a comprehensive summary that includes:
1. Main research question or objective
2. Key methodology
3. Main findings/results
4. Conclusions and implications

Keep the summary concise (300-500 words)."""

SUMMARIZE_FOCUSED = """Summarize the following academic paper with a focus on {focus}:

{content}

Provide a focused summary that emphasizes the {focus} aspects of the paper.
Keep the summary concise (200-400 words)."""

SUMMARIZE_SHORT = """Provide a brief summary of the following academic paper:

{content}

Summarize in 2-3 paragraphs covering:
- What the paper is about
- Key findings
- Main takeaway"""

SUMMARIZE_LONG = """Provide a detailed summary of the following academic paper:

{content}

Include:
1. Introduction and background context
2. Research question/hypothesis
3. Detailed methodology description
4. Key findings with specific data points
5. Discussion of results
6. Limitations mentioned
7. Conclusions and future directions
8. Significance of the work"""

# Report templates
REPORT_READING_GROUP = """Analyze this paper for a reading group discussion:

{content}

Generate a reading group guide with:

## Summary
A 2-3 paragraph summary of the paper.

## Key Arguments
- List the main arguments/claims made in the paper
- Note the evidence provided for each

## Methodology Assessment
- Describe the research approach
- Note any strengths or potential weaknesses

## Discussion Questions
Generate 5-7 thought-provoking questions for group discussion, such as:
- Questions about the methodology
- Questions about alternative interpretations
- Questions about implications and applications

## Critical Points
- What are the paper's main contributions?
- What are potential criticisms or limitations?
- How does this relate to other work in the field?"""

REPORT_REFEREE = """Analyze this paper as a referee/reviewer:

{content}

Generate a referee report with:

## Summary
Brief (1 paragraph) summary of the paper's contribution.

## Main Contributions
List 3-5 main contributions of this paper.

## Strengths
- Identify the strongest aspects of the paper
- Note what the authors do well

## Weaknesses
- Identify limitations or concerns
- Note areas needing improvement

## Specific Comments
Provide detailed comments on:
- Clarity of exposition
- Validity of methodology
- Interpretation of results
- Missing citations or comparisons

## Recommendation
Provide an overall assessment and suggestions for revision."""

REPORT_META = """Extract information for meta-analysis from this paper:

{content}

Provide structured data extraction:

## Study Identification
- Authors:
- Year:
- Title:
- Journal/Source:

## Methodology
- Study design:
- Sample size:
- Population/participants:
- Setting:
- Time period:

## Key Variables
- Independent variable(s):
- Dependent variable(s):
- Control variables:

## Main Results
- Primary effect size(s):
- Confidence intervals:
- P-values:
- Statistical tests used:

## Quality Assessment
- Potential biases:
- Limitations noted:
- Generalizability:

## Notes
Any additional relevant information for meta-analysis."""

REPORT_EXECUTIVE = """Create an executive summary of this paper for non-technical stakeholders:

{content}

Generate an executive summary with:

## Key Takeaway
One sentence capturing the most important finding.

## What This Research Is About
Plain-language explanation of the research topic and why it matters.

## What They Did
Brief description of the approach (avoid technical jargon).

## What They Found
Main findings in accessible language.

## Why It Matters
Practical implications and relevance.

## Limitations to Consider
Key caveats in plain language.

## Bottom Line
2-3 sentences summarizing what decision-makers should know."""

# Study templates
STUDY_SUMMARY = """Summarize this chapter for study purposes:

{content}

Provide a study summary including:

## Chapter Overview
Brief description of what this chapter covers.

## Main Topics
List the main topics/sections covered.

## Key Concepts
Define and explain key concepts introduced.

## Important Points
Bullet points of the most important information to remember.

## Connections
How this relates to other material (if apparent)."""

STUDY_CONCEPTS = """Extract and explain key concepts from this chapter:

{content}

For each major concept:

## Concept Name
- **Definition**: Clear, concise definition
- **Explanation**: More detailed explanation in your own words
- **Example**: A concrete example if applicable
- **Why It Matters**: Significance of this concept

List all important terms and concepts from this chapter."""

STUDY_QUIZ = """Create practice questions based on this chapter:

{content}

Generate study questions at different levels:

## Recall Questions
5 questions testing basic recall of facts and definitions.

## Comprehension Questions
5 questions testing understanding of concepts.

## Application Questions
3 questions requiring application of concepts to new situations.

## Analysis Questions
2 questions requiring deeper analysis or comparison.

For each question, provide the answer after all questions are listed."""

STUDY_FLASHCARDS = """Create flashcards from this chapter:

{content}

Generate flashcards in this format:

---
**Front**: [Question or term]
**Back**: [Answer or definition]
---

Create 15-20 flashcards covering:
- Key term definitions
- Important concepts
- Key facts and figures
- Relationships between concepts"""


def get_summarize_prompt(
    content: str,
    focus: str | None = None,
    length: str = "default",
) -> tuple[str, str]:
    """Get the appropriate summarize prompt.

    Args:
        content: Paper content to summarize.
        focus: Optional focus area.
        length: Length of summary (short, default, long).

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    if focus:
        prompt = SUMMARIZE_FOCUSED.format(content=content, focus=focus)
    elif length == "short":
        prompt = SUMMARIZE_SHORT.format(content=content)
    elif length == "long":
        prompt = SUMMARIZE_LONG.format(content=content)
    else:
        prompt = SUMMARIZE_DEFAULT.format(content=content)

    return SYSTEM_SUMMARIZE, prompt


def get_report_prompt(
    content: str,
    template: str,
) -> tuple[str, str]:
    """Get the appropriate report prompt.

    Args:
        content: Paper content to analyze.
        template: Template name.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    templates = {
        "reading-group": REPORT_READING_GROUP,
        "referee": REPORT_REFEREE,
        "meta": REPORT_META,
        "executive": REPORT_EXECUTIVE,
    }

    template_prompt = templates.get(template, REPORT_READING_GROUP)
    prompt = template_prompt.format(content=content)

    return SYSTEM_REPORT, prompt


def get_study_prompt(
    content: str,
    mode: str,
) -> tuple[str, str]:
    """Get the appropriate study prompt.

    Args:
        content: Chapter content to study.
        mode: Study mode (summary, concepts, quiz, flashcards).

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    templates = {
        "summary": STUDY_SUMMARY,
        "concepts": STUDY_CONCEPTS,
        "quiz": STUDY_QUIZ,
        "flashcards": STUDY_FLASHCARDS,
    }

    template_prompt = templates.get(mode, STUDY_SUMMARY)
    prompt = template_prompt.format(content=content)

    return SYSTEM_STUDY, prompt
