"""Grinding pipeline for Papercutter Factory.

This module handles evidence extraction from ingested papers:
1. Schema definition and auto-generation
2. Evidence extraction matrix
3. Paper synthesis (One-Pager, Appendix Row)
"""

from papercutter.grinding.extractor import (
    ExtractionProgress,
    Extractor,
    ExtractorResult,
    extract_evidence,
)
from papercutter.grinding.generator import (
    SchemaGenerator,
    SuggestedColumn,
    generate_default_schema,
    generate_schema,
)
from papercutter.grinding.matrix import (
    ExtractionMatrix,
    ExtractedValue,
    PaperExtraction,
)
from papercutter.grinding.schema import (
    ExtractionSchema,
    FieldType,
    SchemaField,
    create_economics_schema,
    create_medical_schema,
)
from papercutter.grinding.synthesis import (
    SynthesisResult,
    Synthesizer,
    synthesize_paper,
)

__all__ = [
    # Schema
    "ExtractionSchema",
    "SchemaField",
    "FieldType",
    "create_economics_schema",
    "create_medical_schema",
    # Generator
    "SchemaGenerator",
    "SuggestedColumn",
    "generate_default_schema",
    "generate_schema",
    # Matrix
    "ExtractionMatrix",
    "ExtractedValue",
    "PaperExtraction",
    # Extractor
    "Extractor",
    "ExtractorResult",
    "ExtractionProgress",
    "extract_evidence",
    # Synthesis
    "Synthesizer",
    "SynthesisResult",
    "synthesize_paper",
]
