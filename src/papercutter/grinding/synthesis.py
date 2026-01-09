"""Synthesis module for Papercutter Factory.

Generates summaries and contribution statements for papers:
- One-Pager: Detailed 2500-char summary
- Appendix Row: 3-sentence contribution statement (350 chars)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from papercutter.grinding.matrix import ExtractionMatrix, PaperExtraction
from papercutter.grinding.schema import ExtractionSchema
from papercutter.llm.client import LLMClient, get_client

logger = logging.getLogger(__name__)

# Maximum characters for each synthesis type
ONE_PAGER_MAX_CHARS = 2500
APPENDIX_ROW_MAX_CHARS = 350

# System prompts
ONE_PAGER_SYSTEM = """You are an expert research assistant creating detailed paper summaries for a systematic literature review.

Your summaries should:
1. Be comprehensive but concise (target ~2000-2500 characters)
2. Cover research question, methodology, key findings, and implications
3. Use precise language appropriate for academic audiences
4. Include specific numbers and statistics where available
5. Be written in third person, present tense

Do NOT include:
- Paper titles or author names
- Citations or references
- Personal opinions or evaluations"""

ONE_PAGER_PROMPT = """Create a detailed summary of this paper for inclusion in a systematic review.

Paper content:
{content}

{extraction_context}

Write a ~2000-2500 character summary covering:
1. Research question and motivation
2. Data and methodology
3. Key findings with specific statistics
4. Limitations and implications

Return ONLY the summary text, no headers or formatting."""

APPENDIX_ROW_SYSTEM = """You are an expert research assistant creating concise contribution statements for a systematic review appendix.

Your statements should:
1. Be exactly 2-3 sentences
2. Capture the paper's main contribution to the literature
3. Include the key quantitative finding if applicable
4. Be written in third person, present tense
5. Stay under 350 characters total"""

APPENDIX_ROW_PROMPT = """Create a brief (2-3 sentence, max 350 characters) contribution statement for this paper.

Paper content:
{content}

{extraction_context}

The statement should capture what this paper contributes to the literature and its main finding.

Return ONLY the statement, nothing else."""

COMPRESSION_PROMPT = """Compress this text to fit within {max_chars} characters while preserving the key information:

{text}

Return ONLY the compressed text."""


@dataclass
class SynthesisResult:
    """Result of synthesis for a single paper."""

    paper_id: str
    one_pager: str | None = None
    appendix_row: str | None = None
    one_pager_chars: int = 0
    appendix_row_chars: int = 0
    error: str | None = None


class Synthesizer:
    """Generates summaries and contribution statements for papers.

    Creates:
    - One-Pager: Detailed ~2500 character summary
    - Appendix Row: 2-3 sentence contribution statement (~350 chars)
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        one_pager_max_chars: int = ONE_PAGER_MAX_CHARS,
        appendix_row_max_chars: int = APPENDIX_ROW_MAX_CHARS,
        auto_compress: bool = True,
    ):
        """Initialize the synthesizer.

        Args:
            llm_client: LLM client to use.
            one_pager_max_chars: Maximum characters for one-pager.
            appendix_row_max_chars: Maximum characters for appendix row.
            auto_compress: Automatically compress outputs that exceed limits.
        """
        self.llm_client = llm_client
        self.one_pager_max_chars = one_pager_max_chars
        self.appendix_row_max_chars = appendix_row_max_chars
        self.auto_compress = auto_compress

    def _get_client(self) -> LLMClient:
        """Get or create LLM client."""
        if self.llm_client is None:
            self.llm_client = get_client()
        return self.llm_client

    def synthesize(
        self,
        paper_content: str,
        extraction: PaperExtraction | None = None,
        generate_one_pager: bool = True,
        generate_appendix_row: bool = True,
    ) -> SynthesisResult:
        """Generate synthesis for a paper.

        Args:
            paper_content: Full paper content (markdown).
            extraction: Optional extraction results for context.
            generate_one_pager: Whether to generate one-pager.
            generate_appendix_row: Whether to generate appendix row.

        Returns:
            SynthesisResult with generated summaries.
        """
        result = SynthesisResult(
            paper_id=extraction.paper_id if extraction else "unknown"
        )

        # Build extraction context for prompts
        extraction_context = self._build_extraction_context(extraction)

        # Truncate content if too long (keep ~80k chars for context)
        max_content_chars = 80000
        if len(paper_content) > max_content_chars:
            paper_content = paper_content[:max_content_chars] + "\n\n[Content truncated...]"

        client = self._get_client()

        # Generate one-pager
        if generate_one_pager:
            try:
                prompt = ONE_PAGER_PROMPT.format(
                    content=paper_content,
                    extraction_context=extraction_context,
                )
                response = client.complete(
                    prompt=prompt,
                    system=ONE_PAGER_SYSTEM,
                    max_tokens=1500,
                    temperature=0.3,
                )

                one_pager = response.content.strip()

                # Compress if needed
                if len(one_pager) > self.one_pager_max_chars and self.auto_compress:
                    one_pager = self._compress_text(one_pager, self.one_pager_max_chars)

                result.one_pager = one_pager
                result.one_pager_chars = len(one_pager)

            except Exception as e:
                logger.error(f"Failed to generate one-pager: {e}")
                result.error = str(e)

        # Generate appendix row
        if generate_appendix_row:
            try:
                prompt = APPENDIX_ROW_PROMPT.format(
                    content=paper_content[:20000],  # Use less content for short summary
                    extraction_context=extraction_context,
                )
                response = client.complete(
                    prompt=prompt,
                    system=APPENDIX_ROW_SYSTEM,
                    max_tokens=200,
                    temperature=0.3,
                )

                appendix_row = response.content.strip()

                # Compress if needed
                if len(appendix_row) > self.appendix_row_max_chars and self.auto_compress:
                    appendix_row = self._compress_text(
                        appendix_row, self.appendix_row_max_chars
                    )

                result.appendix_row = appendix_row
                result.appendix_row_chars = len(appendix_row)

            except Exception as e:
                logger.error(f"Failed to generate appendix row: {e}")
                if not result.error:
                    result.error = str(e)

        return result

    def synthesize_matrix(
        self,
        matrix: ExtractionMatrix,
        markdown_dir: Path,
        generate_one_pager: bool = True,
        generate_appendix_row: bool = True,
        progress_callback=None,
    ) -> list[SynthesisResult]:
        """Generate synthesis for all papers in a matrix.

        Args:
            matrix: Extraction matrix with papers.
            markdown_dir: Directory containing markdown files.
            generate_one_pager: Whether to generate one-pagers.
            generate_appendix_row: Whether to generate appendix rows.
            progress_callback: Optional callback(current, total, paper_id).

        Returns:
            List of SynthesisResult for each paper.
        """
        results = []
        papers = list(matrix)
        total = len(papers)

        for i, extraction in enumerate(papers):
            if progress_callback:
                progress_callback(i + 1, total, extraction.paper_id)

            # Find markdown file for this paper
            content = self._load_paper_content(extraction, markdown_dir)

            if not content:
                results.append(
                    SynthesisResult(
                        paper_id=extraction.paper_id,
                        error="Markdown content not found",
                    )
                )
                continue

            # Generate synthesis
            result = self.synthesize(
                paper_content=content,
                extraction=extraction,
                generate_one_pager=generate_one_pager,
                generate_appendix_row=generate_appendix_row,
            )

            # Update extraction in matrix
            extraction.one_pager = result.one_pager
            extraction.appendix_row = result.appendix_row

            results.append(result)

        return results

    def _build_extraction_context(self, extraction: PaperExtraction | None) -> str:
        """Build context string from extraction results."""
        if not extraction or not extraction.extractions:
            return ""

        lines = ["Extracted information:"]
        for key, value in extraction.extractions.items():
            lines.append(f"- {key}: {value.value}")

        return "\n".join(lines)

    def _load_paper_content(
        self,
        extraction: PaperExtraction,
        markdown_dir: Path,
    ) -> str | None:
        """Load markdown content for a paper."""
        # Try different filename patterns
        patterns = [
            f"{extraction.paper_id}.md",
            f"{extraction.bibtex_key}.md" if extraction.bibtex_key else None,
        ]

        # Also try to find by title-based filename
        if extraction.title:
            import re

            title_slug = re.sub(r"[^a-z0-9]+", "_", extraction.title.lower())[:50]
            patterns.append(f"{title_slug}.md")

        for pattern in patterns:
            if pattern:
                path = markdown_dir / pattern
                if path.exists():
                    try:
                        return path.read_text()
                    except Exception as e:
                        logger.warning(f"Failed to read {path}: {e}")

        # Try glob matching
        for md_file in markdown_dir.glob("*.md"):
            if extraction.paper_id in md_file.stem:
                try:
                    return md_file.read_text()
                except Exception:
                    pass

        return None

    def _compress_text(self, text: str, max_chars: int) -> str:
        """Compress text to fit within character limit.

        Args:
            text: Text to compress.
            max_chars: Maximum characters.

        Returns:
            Compressed text.
        """
        if len(text) <= max_chars:
            return text

        try:
            client = self._get_client()
            prompt = COMPRESSION_PROMPT.format(max_chars=max_chars, text=text)

            response = client.complete(
                prompt=prompt,
                max_tokens=max(200, max_chars // 4),
                temperature=0.2,
            )

            compressed = response.content.strip()

            # Hard truncate if still too long
            if len(compressed) > max_chars:
                compressed = compressed[: max_chars - 3] + "..."

            return compressed

        except Exception as e:
            logger.warning(f"Compression failed, truncating: {e}")
            return text[: max_chars - 3] + "..."


def synthesize_paper(
    paper_content: str,
    extraction: PaperExtraction | None = None,
) -> SynthesisResult:
    """Convenience function to synthesize a single paper.

    Args:
        paper_content: Full paper content.
        extraction: Optional extraction results.

    Returns:
        SynthesisResult with one-pager and appendix row.
    """
    synthesizer = Synthesizer()
    return synthesizer.synthesize(paper_content, extraction)
