"""Schema auto-generator for Papercutter Factory.

Generates extraction schemas by sampling papers and using LLM
to suggest appropriate extraction columns.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from papercutter.grinding.schema import ExtractionSchema, FieldType, SchemaField
from papercutter.llm.client import LLMClient, get_client

logger = logging.getLogger(__name__)

# Maximum characters to extract from each paper for schema generation
MAX_SAMPLE_CHARS = 4000

# System prompt for schema generation
SCHEMA_GENERATION_SYSTEM = """You are an expert research assistant helping to design a data extraction schema for a systematic literature review.

Your task is to analyze sample papers and suggest appropriate columns/fields for extracting structured evidence. Consider:
1. What quantitative data should be extracted (sample sizes, effect sizes, etc.)
2. What categorical information should be captured (study type, methodology, etc.)
3. What contextual information is relevant (geography, time period, population, etc.)

For each suggested field, provide:
- A short key name (snake_case, e.g., "sample_size")
- A clear description of what to extract
- The appropriate data type
- Example values or options if applicable"""


SCHEMA_GENERATION_PROMPT = """Based on these sample papers from a research project, suggest 6-10 extraction columns that would be useful for a systematic review.

Sample Paper 1:
{sample_1}

Sample Paper 2:
{sample_2}

Sample Paper 3:
{sample_3}

Return your suggestions as a JSON array with this structure:
[
  {{
    "key": "field_name",
    "description": "What to extract",
    "type": "text|integer|float|boolean|categorical|list",
    "options": ["option1", "option2"],  // Only for categorical
    "example": "Example value",
    "rationale": "Why this field is useful"
  }}
]

Focus on fields that:
1. Capture key quantitative evidence (numbers, statistics)
2. Allow categorization and comparison across papers
3. Are likely to be present in most papers
4. Would be useful for synthesis and reporting

Return ONLY the JSON array, no other text."""


@dataclass
class SuggestedColumn:
    """A suggested extraction column from the generator."""

    key: str
    description: str
    type: FieldType
    options: list[str] | None = None
    example: str | None = None
    rationale: str | None = None

    def to_schema_field(self) -> SchemaField:
        """Convert to SchemaField."""
        return SchemaField(
            key=self.key,
            description=self.description,
            type=self.type,
            options=self.options,
            example=self.example,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SuggestedColumn:
        """Create from dictionary."""
        type_str = data.get("type", "text")
        try:
            field_type = FieldType(type_str)
        except ValueError:
            field_type = FieldType.TEXT

        return cls(
            key=data.get("key", "unknown"),
            description=data.get("description", ""),
            type=field_type,
            options=data.get("options"),
            example=data.get("example"),
            rationale=data.get("rationale"),
        )


@dataclass
class GenerationResult:
    """Result of schema generation."""

    suggestions: list[SuggestedColumn] = field(default_factory=list)
    schema: ExtractionSchema | None = None
    papers_sampled: int = 0
    tokens_used: int = 0
    errors: list[str] = field(default_factory=list)


class SchemaGenerator:
    """Auto-generates extraction schemas from sample papers.

    Uses LLM to analyze sample papers and suggest appropriate
    extraction columns for a systematic review.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        sample_count: int = 3,
        max_sample_chars: int = MAX_SAMPLE_CHARS,
    ):
        """Initialize the generator.

        Args:
            llm_client: LLM client to use (creates default if not provided).
            sample_count: Number of papers to sample.
            max_sample_chars: Max characters to extract per paper.
        """
        self.llm_client = llm_client
        self.sample_count = sample_count
        self.max_sample_chars = max_sample_chars

    def _get_client(self) -> LLMClient:
        """Get or create LLM client."""
        if self.llm_client is None:
            self.llm_client = get_client()
        return self.llm_client

    def generate(
        self,
        markdown_files: list[Path],
        schema_name: str = "Auto-Generated Schema",
    ) -> GenerationResult:
        """Generate extraction schema from sample papers.

        Args:
            markdown_files: List of markdown files to sample from.
            schema_name: Name for the generated schema.

        Returns:
            GenerationResult with suggestions and schema.
        """
        result = GenerationResult()

        if not markdown_files:
            result.errors.append("No markdown files provided")
            return result

        # Sample papers
        samples = self._sample_papers(markdown_files)
        result.papers_sampled = len(samples)

        if len(samples) < 2:
            result.errors.append(
                f"Need at least 2 papers for schema generation, got {len(samples)}"
            )
            return result

        # Pad samples if needed
        while len(samples) < 3:
            samples.append(samples[-1])

        # Generate schema using LLM
        try:
            suggestions = self._call_llm(samples)
            result.suggestions = suggestions

            # Create schema from suggestions
            schema = ExtractionSchema(
                name=schema_name,
                description="Auto-generated schema based on sample papers",
            )
            for suggestion in suggestions:
                schema.fields.append(suggestion.to_schema_field())

            result.schema = schema

        except Exception as e:
            logger.error(f"Schema generation failed: {e}")
            result.errors.append(str(e))

        return result

    def _sample_papers(self, markdown_files: list[Path]) -> list[str]:
        """Sample text from papers.

        Args:
            markdown_files: List of markdown files.

        Returns:
            List of sample texts.
        """
        samples = []

        # Select random files
        files_to_sample = (
            random.sample(markdown_files, min(self.sample_count, len(markdown_files)))
            if len(markdown_files) > self.sample_count
            else markdown_files
        )

        for file in files_to_sample:
            try:
                text = file.read_text()
                # Extract first N characters (abstract + intro typically)
                sample = self._extract_sample(text)
                if sample:
                    samples.append(sample)
            except Exception as e:
                logger.warning(f"Failed to read {file}: {e}")

        return samples

    def _extract_sample(self, text: str) -> str:
        """Extract a representative sample from paper text.

        Focuses on abstract and introduction which usually contain
        the key methodological information.
        """
        # Try to find abstract
        text_lower = text.lower()
        abstract_start = -1

        for marker in ["# abstract", "## abstract", "abstract\n", "**abstract**"]:
            idx = text_lower.find(marker)
            if idx != -1:
                abstract_start = idx
                break

        if abstract_start != -1:
            # Start from abstract
            sample_text = text[abstract_start:]
        else:
            # Start from beginning
            sample_text = text

        # Take first N characters
        return sample_text[: self.max_sample_chars].strip()

    def _call_llm(self, samples: list[str]) -> list[SuggestedColumn]:
        """Call LLM to generate schema suggestions.

        Args:
            samples: List of paper samples.

        Returns:
            List of suggested columns.
        """
        client = self._get_client()

        # Build prompt
        prompt = SCHEMA_GENERATION_PROMPT.format(
            sample_1=samples[0],
            sample_2=samples[1],
            sample_3=samples[2] if len(samples) > 2 else samples[1],
        )

        # Call LLM
        response = client.complete(
            prompt=prompt,
            system=SCHEMA_GENERATION_SYSTEM,
            max_tokens=2000,
            temperature=0.3,
        )

        # Parse response
        return self._parse_suggestions(response.content)

    def _parse_suggestions(self, response: str) -> list[SuggestedColumn]:
        """Parse LLM response into suggestions.

        Args:
            response: Raw LLM response text.

        Returns:
            List of parsed suggestions.
        """
        suggestions = []

        # Try to extract JSON from response
        response = response.strip()

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()

        # Find JSON array
        if not response.startswith("["):
            start = response.find("[")
            if start != -1:
                end = response.rfind("]") + 1
                response = response[start:end]

        try:
            data = json.loads(response)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        suggestions.append(SuggestedColumn.from_dict(item))
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Try line-by-line parsing as fallback
            suggestions = self._parse_suggestions_fallback(response)

        return suggestions

    def _parse_suggestions_fallback(self, response: str) -> list[SuggestedColumn]:
        """Fallback parser for non-JSON responses.

        Attempts to extract field suggestions from free-form text.
        """
        suggestions = []

        # Look for numbered or bulleted items
        import re

        pattern = r"[-*\d.]+\s*\**([a-z_]+)\**[:\s]+(.+?)(?=[-*\d.]|\Z)"
        matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)

        for key, description in matches:
            key = key.strip().lower().replace(" ", "_")
            description = description.strip()
            if key and description:
                suggestions.append(
                    SuggestedColumn(
                        key=key,
                        description=description[:200],
                        type=FieldType.TEXT,
                    )
                )

        return suggestions[:10]  # Limit to 10 suggestions


def generate_schema(
    markdown_files: list[Path],
    output_path: Path | None = None,
    schema_name: str = "Auto-Generated Schema",
) -> ExtractionSchema:
    """Convenience function to generate a schema from papers.

    Args:
        markdown_files: List of markdown files to sample from.
        output_path: Optional path to save the schema YAML.
        schema_name: Name for the schema.

    Returns:
        Generated ExtractionSchema.

    Raises:
        ValueError: If generation fails.
    """
    generator = SchemaGenerator()
    result = generator.generate(markdown_files, schema_name)

    if result.errors:
        raise ValueError(f"Schema generation failed: {result.errors}")

    if result.schema is None:
        raise ValueError("No schema generated")

    if output_path:
        result.schema.save(output_path)
        logger.info(f"Schema saved to {output_path}")

    return result.schema


def generate_default_schema() -> ExtractionSchema:
    """Generate a sensible default schema without LLM.

    Returns:
        Default ExtractionSchema suitable for most research.
    """
    schema = ExtractionSchema(
        name="Default Research Schema",
        description="General-purpose schema for academic research papers",
    )

    # Core fields that apply to most research
    schema.add_field(
        "research_question",
        "The main research question or hypothesis being tested",
        FieldType.TEXT,
    )
    schema.add_field(
        "methodology",
        "Primary research method or study design",
        FieldType.CATEGORICAL,
        options=[
            "Experimental",
            "Observational",
            "Survey",
            "Qualitative",
            "Mixed Methods",
            "Meta-Analysis",
            "Review",
            "Other",
        ],
    )
    schema.add_field(
        "sample_size",
        "Number of observations, participants, or units studied",
        FieldType.TEXT,
        example="N=1,234",
    )
    schema.add_field(
        "data_source",
        "Source of data used in the study",
        FieldType.TEXT,
    )
    schema.add_field(
        "main_finding",
        "Primary result or key finding of the study",
        FieldType.TEXT,
    )
    schema.add_field(
        "limitations",
        "Key limitations acknowledged by the authors",
        FieldType.TEXT,
        required=False,
    )
    schema.add_field(
        "contribution",
        "Main contribution to the literature",
        FieldType.TEXT,
    )

    return schema
