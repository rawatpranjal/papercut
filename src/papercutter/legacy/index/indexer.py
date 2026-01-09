"""Document indexer for creating structure maps."""

import re
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pypdf import PdfReader

# Type alias for page text getter function
PageTextGetter = Callable[[int], str]

from papercutter.legacy.books.splitter import ChapterSplitter
from papercutter.legacy.cache import file_hash, get_cache

# Minimum pages to benefit from parallel processing
_MIN_PAGES_FOR_PARALLEL = 20


def _detect_page_tables(args: tuple[str, int]) -> tuple[int, int]:
    """Detect tables on a single page (for parallel processing).

    Args:
        args: Tuple of (pdf_path_str, page_index).

    Returns:
        Tuple of (page_index, table_count).
    """
    import pdfplumber

    path_str, page_idx = args
    try:
        with pdfplumber.open(path_str) as pdf:
            page = pdf.pages[page_idx]
            return (page_idx, len(page.find_tables()))
    except Exception:
        return (page_idx, 0)


@dataclass
class Section:
    """A detected section in a paper."""

    id: int
    title: str
    pages: tuple[int, int]  # (start, end) 1-indexed


@dataclass
class TableInfo:
    """Metadata about a detected table."""

    id: int
    page: int  # 1-indexed
    caption: str | None = None


@dataclass
class FigureInfo:
    """Metadata about a detected figure."""

    id: int
    page: int  # 1-indexed
    caption: str | None = None


@dataclass
class DocumentIndex:
    """Complete index of a document."""

    id: str  # Hash-based ID
    file: str
    pages: int
    type: Literal["paper", "book"]

    # Metadata
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    abstract: str | None = None

    # Structure (paper)
    sections: list[Section] = field(default_factory=list)

    # Structure (book)
    chapters: list[dict[str, Any]] = field(default_factory=list)

    # Content
    tables: list[TableInfo] = field(default_factory=list)
    figures: list[FigureInfo] = field(default_factory=list)
    refs_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "file": self.file,
            "pages": self.pages,
            "type": self.type,
        }

        if self.title:
            result["metadata"] = {
                "title": self.title,
                "authors": self.authors,
            }

        if self.abstract:
            result["abstract"] = self.abstract

        if self.type == "paper" and self.sections:
            result["sections"] = [
                {"id": s.id, "title": s.title, "pages": list(s.pages)}
                for s in self.sections
            ]
        elif self.type == "book" and self.chapters:
            result["chapters"] = self.chapters

        if self.tables:
            result["tables"] = [
                {"id": t.id, "page": t.page, "caption": t.caption}
                for t in self.tables
            ]

        if self.figures:
            result["figures"] = [
                {"id": f.id, "page": f.page, "caption": f.caption}
                for f in self.figures
            ]

        if self.refs_count > 0:
            result["refs_count"] = self.refs_count

        return result


class DocumentIndexer:
    """Index documents by detecting structure and content."""

    # Patterns to skip when extracting title (copyright, legal, publishing info)
    SKIP_TITLE_PATTERNS = [
        r"^Copyright",
        r"^©",
        r"^\d{4}\s+.*(?:Press|Publishing|Inc\.|Ltd\.|LLC)",
        r"^All rights reserved",
        r"^ISBN",
        r"^Published by",
        r"^Printed in",
        r"^First published",
        r"^Reprinted",
        r"^This edition",
        r"^Library of Congress",
        r"^British Library",
        r"^CIP data",
        r"^Cataloguing",
        r"^On-screen viewing",
    ]

    # Section patterns for academic papers
    SECTION_PATTERNS = [
        # Numbered sections: "1. Introduction", "2. Methods"
        r"^(\d+\.?\s+)(Introduction|Background|Literature Review|Related Work)",
        r"^(\d+\.?\s+)(Methods?|Methodology|Data|Materials?)",
        r"^(\d+\.?\s+)(Results?|Findings|Analysis)",
        r"^(\d+\.?\s+)(Discussion|Conclusions?|Summary)",
        r"^(\d+\.?\s+)(References?|Bibliography)",
        r"^(\d+\.?\s+)(Appendix|Appendices)",
        r"^(\d+\.?\s+)(Experimental|Experiments?)",
        r"^(\d+\.?\s+)(Theory|Theoretical)",
        r"^(\d+\.?\s+)(Model|Framework)",
        r"^(\d+\.?\s+)(Implementation|Design)",
        r"^(\d+\.?\s+)(Evaluation|Validation)",
        r"^(\d+\.?\s+)(Future Work|Limitations)",
        # Numbered subsections: "1.1 Background"
        r"^(\d+\.\d+\.?\s+)([A-Z][a-z]+)",
        # Roman numerals: "I. Introduction"
        r"^([IVXLC]+\.?\s+)(Introduction|Methods?|Results?|Discussion|Conclusions?)",
        r"^([IVXLC]+\.?\s+)([A-Z][a-z]+)",
        # Unnumbered common sections
        r"^(Abstract)$",
        r"^(Introduction)$",
        r"^(Methods?|Methodology)$",
        r"^(Data and Methods?)$",
        r"^(Materials?\s+and\s+Methods?)$",
        r"^(Experimental\s+Section)$",
        r"^(Results?)$",
        r"^(Results?\s+and\s+Discussion)$",
        r"^(Discussion)$",
        r"^(Conclusions?|Concluding\s+Remarks?)$",
        r"^(Summary)$",
        r"^(Acknowledgments?|Acknowledgements?)$",
        r"^(References?|Bibliography)$",
        r"^(Supplementary\s+Materials?)$",
    ]

    # Abstract detection patterns
    ABSTRACT_PATTERNS = [
        r"(?:^|\n)Abstract[:\s]*\n(.+?)(?=\n\s*\n|\nIntroduction|\n1\.)",
        r"(?:^|\n)ABSTRACT[:\s]*\n(.+?)(?=\n\s*\n|\nINTRODUCTION|\n1\.)",
    ]

    # Pre-compiled patterns for performance
    _COMPILED_SECTION_PATTERNS: list[re.Pattern] | None = None
    _COMPILED_ABSTRACT_PATTERNS: list[re.Pattern] | None = None
    _REF_SECTION_PATTERN = re.compile(r'^(References?|Bibliography)', re.IGNORECASE | re.MULTILINE)
    _REF_NUMBERED_PATTERN = re.compile(r'^\s*\[?\d+[\.\])]', re.MULTILINE)
    _REF_AUTHOR_YEAR_PATTERN = re.compile(r'^[A-Z][a-z]+,?\s+[A-Z]', re.MULTILINE)

    @classmethod
    def _get_compiled_section_patterns(cls) -> list[re.Pattern]:
        """Get compiled section patterns (lazy initialization)."""
        if cls._COMPILED_SECTION_PATTERNS is None:
            cls._COMPILED_SECTION_PATTERNS = [
                re.compile(p, re.IGNORECASE | re.MULTILINE)
                for p in cls.SECTION_PATTERNS
            ]
        return cls._COMPILED_SECTION_PATTERNS

    @classmethod
    def _get_compiled_abstract_patterns(cls) -> list[re.Pattern]:
        """Get compiled abstract patterns (lazy initialization)."""
        if cls._COMPILED_ABSTRACT_PATTERNS is None:
            cls._COMPILED_ABSTRACT_PATTERNS = [
                re.compile(p, re.DOTALL | re.IGNORECASE)
                for p in cls.ABSTRACT_PATTERNS
            ]
        return cls._COMPILED_ABSTRACT_PATTERNS

    def __init__(self, use_cache: bool = True, parallel: bool = False):
        """Initialize the indexer.

        Args:
            use_cache: Whether to use caching.
            parallel: Enable parallel processing for large documents.
        """
        self.use_cache = use_cache
        self.parallel = parallel
        self.cache = get_cache() if use_cache else None
        self.chapter_splitter = ChapterSplitter()

    def index(
        self,
        pdf_path: Path,
        doc_type: Literal["paper", "book"] | None = None,
        force: bool = False,
    ) -> DocumentIndex:
        """Index a PDF document.

        Args:
            pdf_path: Path to the PDF file.
            doc_type: Document type (auto-detected if not specified).
            force: Force re-indexing even if cached.

        Returns:
            DocumentIndex with structure information.
        """
        pdf_path = Path(pdf_path)

        # Check cache
        if self.use_cache and not force and self.cache is not None:
            cached = self.cache.get_index(pdf_path)
            if cached:
                return self._dict_to_index(cached)

        # Build index
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Page text cache to avoid redundant extraction
        # (pages are extracted multiple times by different methods)
        page_text_cache: dict[int, str] = {}

        def get_page_text(page_num: int) -> str:
            """Get page text with caching."""
            if page_num not in page_text_cache:
                if 0 <= page_num < total_pages:
                    page_text_cache[page_num] = reader.pages[page_num].extract_text(extraction_mode="layout") or ""
                else:
                    page_text_cache[page_num] = ""
            return page_text_cache[page_num]

        # Auto-detect type if not specified
        if doc_type is None:
            doc_type = self._detect_type(reader, total_pages, get_page_text)

        # Create base index
        doc_id = file_hash(pdf_path)
        index = DocumentIndex(
            id=doc_id,
            file=str(pdf_path.name),
            pages=total_pages,
            type=doc_type,
        )

        # Extract metadata
        self._extract_metadata(reader, index, get_page_text)

        # Extract structure based on type
        if doc_type == "book":
            self._index_book(pdf_path, reader, index)
        else:
            self._index_paper(reader, index, get_page_text)

        # Extract tables and figures info
        self._detect_tables(pdf_path, index)
        self._count_references(reader, index, get_page_text)

        # Cache result
        if self.use_cache and self.cache is not None:
            self.cache.set_index(pdf_path, index.to_dict())

        return index

    def _detect_type(
        self,
        reader: PdfReader,
        total_pages: int,
        get_page_text: PageTextGetter,
    ) -> Literal["paper", "book"]:
        """Auto-detect document type.

        Heuristics:
        - Books typically have 50+ pages
        - Books have chapter patterns or bookmarks
        - Papers typically have abstract + numbered sections
        """
        # Check page count
        if total_pages >= 50:
            # Actually check via bookmarks
            if reader.outline:
                return "book"

            # Check first few pages for chapter patterns
            for page_num in range(min(5, total_pages)):
                text = get_page_text(page_num)
                for pattern in self.chapter_splitter.CHAPTER_PATTERNS:
                    if re.search(pattern, text[:500], re.MULTILINE):
                        return "book"

        return "paper"

    def _extract_metadata(
        self,
        reader: PdfReader,
        index: DocumentIndex,
        get_page_text: PageTextGetter,
    ) -> None:
        """Extract document metadata."""
        # Try PDF metadata first
        if reader.metadata:
            if reader.metadata.title:
                index.title = reader.metadata.title
            if reader.metadata.author:
                index.authors = [reader.metadata.author]

        # Try to extract from first page
        if not index.title and reader.pages:
            first_page_text = get_page_text(0)
            lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]

            # Title is usually the first non-empty line that's substantial
            # but we need to skip copyright notices and legal text
            for line in lines[:15]:  # Check more lines for books
                # Skip if too short or URL
                if len(line) < 10 or line.startswith("http"):
                    continue
                # Skip copyright/legal/publishing lines
                if any(re.match(p, line, re.IGNORECASE) for p in self.SKIP_TITLE_PATTERNS):
                    continue
                index.title = line[:200]  # Truncate long titles
                break

        # Extract abstract
        if reader.pages:
            first_pages_text = ""
            for i in range(min(3, len(reader.pages))):
                first_pages_text += get_page_text(i) + "\n"

            for pattern in self._get_compiled_abstract_patterns():
                match = pattern.search(first_pages_text)
                if match:
                    abstract = match.group(1).strip()
                    # Clean up and truncate
                    abstract = re.sub(r'\s+', ' ', abstract)
                    if len(abstract) > 1000:
                        abstract = abstract[:1000] + "..."
                    index.abstract = abstract
                    break

    def _index_paper(
        self,
        reader: PdfReader,
        index: DocumentIndex,
        get_page_text: PageTextGetter,
    ) -> None:
        """Index a paper document (detect sections)."""
        sections = []
        section_id = 0

        compiled_patterns = self._get_compiled_section_patterns()

        section_starts = []  # (page_num, title)

        for page_num in range(len(reader.pages)):
            text = get_page_text(page_num)
            lines = text.split("\n")

            for line in lines:  # Check all lines on each page for section headers
                line = line.strip()
                for pattern in compiled_patterns:
                    if pattern.match(line):
                        # Found a section header
                        title = line[:100]  # Truncate
                        section_starts.append((page_num, title))
                        break

        # Sort section_starts by page number and deduplicate same-page entries
        section_starts.sort(key=lambda x: x[0])
        # Keep only first section found per page to avoid duplicates
        seen_pages = set()
        unique_sections = []
        for page_num, title in section_starts:
            if page_num not in seen_pages:
                seen_pages.add(page_num)
                unique_sections.append((page_num, title))
        section_starts = unique_sections

        # Convert to sections with page ranges
        # Pages are stored as (start_1idx, end_1idx) - both 1-indexed, inclusive
        for i, (page_num, title) in enumerate(section_starts):
            section_id += 1
            start_page = page_num + 1  # Convert 0-indexed to 1-indexed

            if i + 1 < len(section_starts):
                # End page is the page before the next section starts
                # Next section's 0-indexed page N means current ends on 1-indexed page N
                next_section_0idx = section_starts[i + 1][0]
                end_page = max(next_section_0idx, start_page)  # Ensure end >= start
            else:
                # Last section extends to end of document
                end_page = len(reader.pages)

            sections.append(Section(
                id=section_id,
                title=title,
                pages=(start_page, end_page),
            ))

        index.sections = sections

    def _index_book(self, pdf_path: Path, reader: PdfReader, index: DocumentIndex) -> None:
        """Index a book document (detect chapters)."""
        chapters = self.chapter_splitter.detect_chapters(pdf_path)

        index.chapters = [
            {
                "id": i + 1,
                "title": ch.title,
                "pages": [ch.start_page + 1, ch.end_page],  # 1-indexed
            }
            for i, ch in enumerate(chapters)
        ]

    def _detect_tables(self, pdf_path: Path, index: DocumentIndex) -> None:
        """Detect tables in the document.

        Uses parallel processing for large documents when self.parallel is True.
        """
        import pdfplumber

        tables = []
        table_id = 0

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

                # Use parallel detection for large documents
                if self.parallel and total_pages >= _MIN_PAGES_FOR_PARALLEL:
                    table_counts = self._detect_tables_parallel(pdf_path, total_pages)
                    for page_num in sorted(table_counts.keys()):
                        for _ in range(table_counts[page_num]):
                            table_id += 1
                            tables.append(TableInfo(
                                id=table_id,
                                page=page_num + 1,  # 1-indexed
                                caption=None,
                            ))
                else:
                    # Sequential detection
                    for page_num, page in enumerate(pdf.pages):
                        page_tables = page.find_tables()
                        for _ in page_tables:
                            table_id += 1
                            tables.append(TableInfo(
                                id=table_id,
                                page=page_num + 1,  # 1-indexed
                                caption=None,
                            ))
        except Exception:
            pass  # Skip table detection on error

        index.tables = tables

    def _detect_tables_parallel(
        self, pdf_path: Path, total_pages: int
    ) -> dict[int, int]:
        """Detect tables in parallel across pages.

        Args:
            pdf_path: Path to the PDF file.
            total_pages: Total number of pages.

        Returns:
            Dict mapping page_num to table count on that page.
        """
        path_str = str(pdf_path.absolute())
        args = [(path_str, idx) for idx in range(total_pages)]

        results: dict[int, int] = {}
        max_workers = min(4, total_pages)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_detect_page_tables, arg): arg[1] for arg in args
            }
            for future in as_completed(futures):
                page_idx, count = future.result()
                if count > 0:
                    results[page_idx] = count

        return results

    def _count_references(
        self,
        reader: PdfReader,
        index: DocumentIndex,
        get_page_text: PageTextGetter,
    ) -> None:
        """Count references in the document.

        Uses heuristics to detect reference format (numbered vs author-year) and
        counts accordingly. Only uses one format to avoid double-counting.
        """
        total_pages = len(reader.pages)

        # Scan last 50 pages for books, last 10 for papers
        pages_to_scan = 50 if index.type == "book" else 10
        pages_to_scan = min(pages_to_scan, total_pages)

        numbered_count = 0
        author_year_count = 0
        found_refs_section = False

        for page_num in range(max(0, total_pages - pages_to_scan), total_pages):
            text = get_page_text(page_num)

            # Check if this is a references page
            if self._REF_SECTION_PATTERN.search(text):
                found_refs_section = True
                # Count both styles separately
                numbered_count += len(self._REF_NUMBERED_PATTERN.findall(text))
                author_year_count += len(self._REF_AUTHOR_YEAR_PATTERN.findall(text))

        # Use the count from whichever format is dominant (avoid double-counting)
        # If numbered refs found, prefer those as they're more reliable
        if numbered_count > 0:
            index.refs_count = numbered_count
        elif found_refs_section:
            index.refs_count = author_year_count
        else:
            index.refs_count = 0

    def _dict_to_index(self, data: dict[str, Any]) -> DocumentIndex:
        """Convert dict back to DocumentIndex."""
        index = DocumentIndex(
            id=data["id"],
            file=data["file"],
            pages=data["pages"],
            type=data["type"],
        )

        if "metadata" in data:
            index.title = data["metadata"].get("title")
            index.authors = data["metadata"].get("authors", [])

        if "abstract" in data:
            index.abstract = data["abstract"]

        if "sections" in data:
            index.sections = [
                Section(id=s["id"], title=s["title"], pages=tuple(s["pages"]))
                for s in data["sections"]
            ]

        if "chapters" in data:
            index.chapters = data["chapters"]

        if "tables" in data:
            index.tables = [
                TableInfo(id=t["id"], page=t["page"], caption=t.get("caption"))
                for t in data["tables"]
            ]

        if "figures" in data:
            index.figures = [
                FigureInfo(id=f["id"], page=f["page"], caption=f.get("caption"))
                for f in data["figures"]
            ]

        if "refs_count" in data:
            index.refs_count = data["refs_count"]

        return index
