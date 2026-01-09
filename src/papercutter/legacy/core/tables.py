"""Table extraction logic."""

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from papercutter.extractors.base import Extractor


@dataclass
class ExtractedTable:
    """Represents an extracted table from a PDF."""

    page: int
    data: list[list[str]]
    bbox: tuple[float, float, float, float] | None = None
    confidence: float = 1.0  # Confidence score 0.0-1.0
    extraction_method: str = "pdfplumber"  # Track extraction method

    @property
    def rows(self) -> int:
        """Number of rows in the table."""
        return len(self.data)

    @property
    def cols(self) -> int:
        """Number of columns in the table."""
        return len(self.data[0]) if self.data else 0

    @property
    def headers(self) -> list[str]:
        """Get the first row as headers."""
        return self.data[0] if self.data else []

    def to_csv(self) -> str:
        """Convert table to CSV string.

        Returns:
            CSV formatted string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        for row in self.data:
            # Clean up cell values
            cleaned_row = [self._clean_cell(cell) for cell in row]
            writer.writerow(cleaned_row)

        return output.getvalue()

    def to_json(self) -> str:
        """Convert table to JSON string.

        Returns:
            JSON formatted string with table data.
        """
        # Clean up data
        cleaned_data = [
            [self._clean_cell(cell) for cell in row] for row in self.data
        ]

        return json.dumps(
            {
                "page": self.page,
                "rows": self.rows,
                "cols": self.cols,
                "data": cleaned_data,
            },
            indent=2,
        )

    def to_dict_rows(self) -> list[dict[str, str]]:
        """Convert table to list of dictionaries using first row as headers.

        Returns:
            List of row dictionaries.
        """
        if len(self.data) < 2:
            return []

        headers = [self._clean_cell(h) or f"col_{i}" for i, h in enumerate(self.headers)]
        rows = []

        for row in self.data[1:]:
            row_dict = {}
            for i, cell in enumerate(row):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_dict[key] = self._clean_cell(cell)
            rows.append(row_dict)

        return rows

    def _clean_cell(self, cell: Any) -> str:
        """Clean a cell value.

        Args:
            cell: Raw cell value.

        Returns:
            Cleaned string value.
        """
        if cell is None:
            return ""
        # Convert to string and clean whitespace
        return str(cell).strip().replace("\n", " ")

    def compute_confidence(self) -> float:
        """Compute heuristic confidence score for this table.

        Scores are based on common extraction quality issues:
        - Empty cells (many empty cells = lower confidence)
        - Column inconsistency (rows with different column counts)
        - Garbled text (non-ASCII clusters, split numbers)
        - Single-character cells (OCR artifacts)

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        score = 1.0
        total_cells = sum(len(row) for row in self.data)

        if total_cells == 0:
            return 0.0

        # Penalty 1: Empty cell ratio
        empty = sum(
            1 for row in self.data for c in row
            if not str(c).strip()
        )
        empty_ratio = empty / total_cells
        if empty_ratio > 0.5:
            score -= 0.3
        elif empty_ratio > 0.3:
            score -= 0.15

        # Penalty 2: Column inconsistency
        col_counts = [len(row) for row in self.data]
        if col_counts:
            mode = max(set(col_counts), key=col_counts.count)
            inconsistent = sum(1 for c in col_counts if c != mode)
            inconsistency_ratio = inconsistent / len(col_counts)
            if inconsistency_ratio > 0.3:
                score -= 0.25
            elif inconsistency_ratio > 0.1:
                score -= 0.1

        # Penalty 3: Garbled text (non-ASCII clusters, split numbers like "0.03 42")
        garbled_pattern = re.compile(r'[^\x00-\x7F]{3,}|\d\s+\d')
        garbled = sum(
            1 for row in self.data for c in row
            if garbled_pattern.search(str(c))
        )
        if garbled > 0:
            score -= 0.2 * min(garbled / total_cells, 1.0)

        # Penalty 4: Single-character cells (OCR artifacts)
        short = sum(
            1 for row in self.data for c in row
            if 0 < len(str(c).strip()) < 2
        )
        if short > total_cells * 0.3:
            score -= 0.15

        # Penalty 5: Very small table (might be fragment)
        if self.rows < 3 or self.cols < 2:
            score -= 0.2

        return max(0.0, min(1.0, score))


class TableExtractor:
    """Extract tables from PDFs."""

    # Valid strictness levels
    STRICTNESS_LEVELS = ("permissive", "standard", "strict")

    def __init__(self, backend: Extractor, strictness: str = "standard"):
        """Initialize with an extraction backend.

        Args:
            backend: PDF extraction backend (e.g., PdfPlumberExtractor).
            strictness: Validation strictness level.
                - "permissive": Minimal filtering (only reject empty tables)
                - "standard": Balanced filtering (20% content, 40% column consistency)
                - "strict": Aggressive filtering (20% content, 50% column consistency)
        """
        if strictness not in self.STRICTNESS_LEVELS:
            raise ValueError(
                f"Invalid strictness: {strictness}. "
                f"Must be one of: {', '.join(self.STRICTNESS_LEVELS)}"
            )
        self.backend = backend
        self.strictness = strictness

    def extract(
        self,
        path: Path,
        pages: list[int] | None = None,
        table_settings: dict[str, Any] | None = None,
    ) -> list[ExtractedTable]:
        """Extract all tables from PDF.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.
            table_settings: Optional dict of pdfplumber table detection settings.
                Keys: vertical_strategy, horizontal_strategy, snap_tolerance,
                join_tolerance, edge_min_length, min_words_vertical, min_words_horizontal.

        Returns:
            List of ExtractedTable objects.
        """
        raw_tables = self.backend.extract_tables(path, pages, table_settings)

        validated_tables = []
        for table in raw_tables:
            if not table["data"]:  # Skip empty tables
                continue

            # Validate that this looks like a real table
            if self._is_valid_table(table["data"]):
                validated_tables.append(
                    ExtractedTable(
                        page=table["page"],
                        data=table["data"],
                        bbox=table.get("bbox"),
                    )
                )

        return validated_tables

    def _is_valid_table(self, data: list[list[Any]]) -> bool:
        """Validate that data looks like a real table.

        Validation strictness is controlled by self.strictness:
        - "permissive": Only rejects empty tables and single-row/column tables
        - "standard": Also requires 20% non-empty cells and 40% column consistency
        - "strict": Also requires 50% column consistency

        Args:
            data: 2D list of cell values.

        Returns:
            True if this looks like a valid table.
        """
        # Basic checks (all strictness levels)
        # Need at least 2 rows (header + 1 data row)
        if not data or len(data) < 2:
            return False

        # Count columns in each row
        col_counts = [len(row) for row in data]
        if not col_counts:
            return False

        # Need at least 2 columns
        max_cols = max(col_counts)
        if max_cols < 2:
            return False

        # Count non-empty cells
        non_empty = sum(
            1 for row in data for cell in row
            if cell is not None and str(cell).strip()
        )

        # Need at least 1 non-empty cell (all strictness levels)
        if non_empty == 0:
            return False

        # Permissive mode: stop here
        if self.strictness == "permissive":
            return True

        # Standard and strict modes: require 20% non-empty cells
        total_cells = sum(len(row) for row in data)
        if total_cells > 0 and non_empty / total_cells < 0.20:
            return False

        # Column consistency check
        # Calculate mode (most common column count)
        mode_count = max(set(col_counts), key=col_counts.count)
        consistent = sum(1 for c in col_counts if c == mode_count)

        # Threshold depends on strictness
        threshold = 0.5 if self.strictness == "strict" else 0.4
        if consistent / len(col_counts) < threshold:
            return False

        return True

    def extract_as_csv(
        self,
        path: Path,
        pages: list[int] | None = None,
        table_settings: dict[str, Any] | None = None,
    ) -> list[tuple[int, str]]:
        """Extract all tables as CSV strings.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.
            table_settings: Optional pdfplumber table detection settings.

        Returns:
            List of (page_number, csv_string) tuples.
        """
        tables = self.extract(path, pages, table_settings)
        return [(t.page, t.to_csv()) for t in tables]

    def extract_hybrid(
        self,
        path: Path,
        pages: list[int] | None = None,
    ) -> list[ExtractedTable]:
        """Extract tables using both lines and text strategies, merged.

        This method tries both pdfplumber detection strategies:
        - "lines": Works well for tables with visible borders
        - "text": Works well for borderless tables (common in economics papers)

        Results are merged and deduplicated, preferring larger tables.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.

        Returns:
            Deduplicated list of tables from both strategies.
        """
        # Try lines strategy (default, good for bordered tables)
        lines_tables = self.extract(path, pages, table_settings={
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
        })

        # Try text strategy (good for borderless tables)
        text_tables = self.extract(path, pages, table_settings={
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 5,
        })

        # Merge and dedupe by page + size
        return self._merge_tables(lines_tables, text_tables)

    def _merge_tables(
        self,
        tables1: list[ExtractedTable],
        tables2: list[ExtractedTable],
    ) -> list[ExtractedTable]:
        """Merge two table lists, preferring larger tables on same page.

        Args:
            tables1: First list of tables.
            tables2: Second list of tables.

        Returns:
            Merged and deduplicated list.
        """
        # Group by page
        by_page: dict[int, list[ExtractedTable]] = {}
        for t in tables1 + tables2:
            by_page.setdefault(t.page, []).append(t)

        merged = []
        for page_tables in by_page.values():
            # Sort by size (rows * cols), largest first
            page_tables.sort(key=lambda t: t.rows * t.cols, reverse=True)

            # Keep non-overlapping tables
            kept_tables: list[ExtractedTable] = []
            for t in page_tables:
                # Check if this table significantly overlaps with any kept table
                overlaps = False
                for kept in kept_tables:
                    # Simple heuristic: if row counts are similar and on same page, likely overlap
                    if abs(t.rows - kept.rows) <= 2 and abs(t.cols - kept.cols) <= 2:
                        overlaps = True
                        break
                if not overlaps:
                    kept_tables.append(t)

            merged.extend(kept_tables)

        # Sort final result by page
        merged.sort(key=lambda t: t.page)
        return merged

    def extract_with_fallback(
        self,
        path: Path,
        pages: list[int] | None = None,
        confidence_threshold: float = 0.5,
        force_llm: bool = False,
        offline: bool = False,
        vision_model: str = "gpt-4o-mini",
    ) -> list[ExtractedTable]:
        """Extract tables with optional LLM vision fallback.

        This method first tries traditional extraction, then uses vision LLM
        for pages where extraction confidence is below the threshold.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.
            confidence_threshold: Minimum confidence to accept traditional extraction.
                Tables below this threshold trigger LLM fallback.
            force_llm: If True, skip traditional extraction and use LLM for all pages.
            offline: If True, never use LLM (traditional extraction only).
            vision_model: Model to use for vision extraction.

        Returns:
            List of ExtractedTable objects.

        Raises:
            LLMNotAvailableError: If LLM is needed but not configured.
        """
        # Step 1: Traditional extraction (unless forcing LLM)
        if not force_llm:
            tables = self.extract_hybrid(path, pages)

            # Compute confidence for each table
            for t in tables:
                t.confidence = t.compute_confidence()

            if offline:
                return tables
        else:
            tables = []

        # Step 2: Identify pages needing LLM extraction
        high_confidence_tables = [
            t for t in tables if t.confidence >= confidence_threshold
        ]
        low_confidence_pages = {
            t.page for t in tables if t.confidence < confidence_threshold
        }
        processed_pages = {t.page for t in high_confidence_tables}

        # If forcing LLM, determine which pages to process
        if force_llm:
            page_count = self.backend.get_page_count(path)
            if pages is not None:
                low_confidence_pages = set(p + 1 for p in pages)  # Convert to 1-indexed
            else:
                low_confidence_pages = set(range(1, page_count + 1))

        # Step 3: Vision LLM fallback for low-confidence pages
        pages_to_process = low_confidence_pages - processed_pages
        if pages_to_process:
            vision_tables = self._extract_via_vision(
                path,
                sorted(pages_to_process),
                vision_model,
            )
            high_confidence_tables.extend(vision_tables)

        # Sort by page and return
        high_confidence_tables.sort(key=lambda t: t.page)
        return high_confidence_tables

    def _extract_via_vision(
        self,
        path: Path,
        pages: list[int],
        model: str,
    ) -> list[ExtractedTable]:
        """Extract tables from specific pages using vision LLM.

        Args:
            path: Path to the PDF file.
            pages: List of 1-indexed page numbers to process.
            model: Vision model to use.

        Returns:
            List of ExtractedTable objects.
        """
        from papercutter.legacy.core.vision import PageRenderer
        from papercutter.llm import get_client
        from papercutter.llm.schemas import TABLE_EXTRACTION_PROMPT, VisionTable

        renderer = PageRenderer()
        client = get_client()

        results = []
        for page_num in pages:
            try:
                # Render page (0-indexed internally)
                rendered = renderer.render_page(path, page_num - 1)

                # Extract via vision LLM
                vision_result = client.complete_structured(
                    prompt=TABLE_EXTRACTION_PROMPT,
                    response_model=VisionTable,
                    images=[rendered.image_data],
                    model=model,
                )

                # Convert to ExtractedTable if we got data
                if vision_result.headers or vision_result.rows:
                    data = vision_result.to_data_list()
                    results.append(
                        ExtractedTable(
                            page=page_num,
                            data=data,
                            confidence=0.9,  # Vision extractions are high confidence
                            extraction_method="vision-llm",
                        )
                    )

            except Exception as e:
                # Log but continue with other pages
                import logging
                logging.warning(f"Vision extraction failed for page {page_num}: {e}")
                continue

        return results

    def estimate_fallback_cost(
        self,
        path: Path,
        pages: list[int] | None = None,
        confidence_threshold: float = 0.5,
    ) -> dict[str, Any]:
        """Estimate cost of LLM fallback without running it.

        Args:
            path: Path to the PDF file.
            pages: Optional list of 0-indexed page numbers.
            confidence_threshold: Confidence threshold for fallback.

        Returns:
            Dictionary with cost estimation details.
        """

        # Run traditional extraction to get confidence scores
        tables = self.extract_hybrid(path, pages)
        for t in tables:
            t.confidence = t.compute_confidence()

        low_confidence = [t for t in tables if t.confidence < confidence_threshold]
        low_confidence_pages = list({t.page for t in low_confidence})

        # Estimate cost (~$0.002 per page for gpt-4o-mini)
        cost_per_page = 0.002
        estimated_cost = len(low_confidence_pages) * cost_per_page

        return {
            "tables_found": len(tables),
            "high_confidence": len(tables) - len(low_confidence),
            "low_confidence": len(low_confidence),
            "pages_needing_fallback": sorted(low_confidence_pages),
            "estimated_cost_usd": round(estimated_cost, 4),
            "confidence_threshold": confidence_threshold,
        }
