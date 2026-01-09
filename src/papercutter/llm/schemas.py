"""Pydantic schemas for vision LLM structured outputs."""

from pydantic import BaseModel, Field


class TableRow(BaseModel):
    """A single row in a table."""

    cells: list[str] = Field(description="Cell values in order, left to right")


class VisionTable(BaseModel):
    """Schema for a table extracted by vision LLM.

    Used with instructor for reliable structured extraction from page images.
    """

    headers: list[str] = Field(
        description="Column headers from the first row of the table"
    )
    rows: list[TableRow] = Field(
        description="Data rows (excluding header row)"
    )
    caption: str | None = Field(
        None,
        description="Table caption or title if visible"
    )
    notes: str | None = Field(
        None,
        description="Footnotes or notes below the table"
    )

    def to_data_list(self) -> list[list[str]]:
        """Convert to a 2D list format compatible with ExtractedTable.

        Returns:
            List of rows, with headers as first row.
        """
        return [self.headers] + [row.cells for row in self.rows]


class VisionReference(BaseModel):
    """Schema for a single bibliographic reference extracted by vision LLM."""

    authors: list[str] = Field(
        description="Author names in 'Firstname Lastname' format"
    )
    title: str = Field(
        description="Title of the paper, article, or book"
    )
    year: int | None = Field(
        None,
        description="Publication year"
    )
    journal: str | None = Field(
        None,
        description="Journal, conference, or venue name"
    )
    volume: str | None = Field(
        None,
        description="Volume number"
    )
    issue: str | None = Field(
        None,
        description="Issue number"
    )
    pages: str | None = Field(
        None,
        description="Page range (e.g., '123-145')"
    )
    doi: str | None = Field(
        None,
        description="DOI in format '10.xxxx/...' if present"
    )
    url: str | None = Field(
        None,
        description="URL if present and no DOI"
    )


class VisionReferences(BaseModel):
    """Schema for multiple references extracted from bibliography pages."""

    references: list[VisionReference] = Field(
        description="List of extracted references"
    )


# Prompts for vision extraction
TABLE_EXTRACTION_PROMPT = """Extract the table from this PDF page image.

Instructions:
1. Identify all column headers (from the header row)
2. Extract each data row, preserving exact cell values
3. Handle merged cells by repeating values where appropriate
4. Preserve numbers, symbols, asterisks (*), and formatting exactly
5. If text is unclear, use "[unclear]" as placeholder
6. Include table caption if visible
7. Include footnotes/notes if present

IMPORTANT for regression/statistics tables:
- Standard errors are often in parentheses - keep them with their values
- Significance stars (*, **, ***) must be preserved exactly
- "N", "Observations", "R-squared" rows are data, not notes

Return structured data matching the schema."""

REFERENCE_EXTRACTION_PROMPT = """Extract the bibliographic references from this PDF page image.

Instructions:
1. Parse each reference entry separately
2. Extract authors as a list: ["Firstname Lastname", "Firstname Lastname"]
3. Extract the paper/book title (not the journal name)
4. Extract year as an integer
5. Extract journal/venue name if applicable
6. Extract volume, issue, pages if present
7. Extract DOI if present (format: "10.xxxx/...")

COMMON MISTAKES TO AVOID:
- Do NOT put journal name in the authors field
- Do NOT put title in the authors field
- Conference papers: put venue in journal field

Return structured data matching the schema."""
