"""Document indexer for creating structure maps."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

from pypdf import PdfReader

from papercut.cache import file_hash, get_cache
from papercut.books.splitter import ChapterSplitter


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
    caption: Optional[str] = None


@dataclass
class FigureInfo:
    """Metadata about a detected figure."""

    id: int
    page: int  # 1-indexed
    caption: Optional[str] = None


@dataclass
class DocumentIndex:
    """Complete index of a document."""

    id: str  # Hash-based ID
    file: str
    pages: int
    type: Literal["paper", "book"]

    # Metadata
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    abstract: Optional[str] = None

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

    # Section patterns for academic papers
    SECTION_PATTERNS = [
        # Numbered sections: "1. Introduction", "2. Methods"
        r"^(\d+\.?\s+)(Introduction|Background|Literature Review|Related Work)",
        r"^(\d+\.?\s+)(Methods?|Methodology|Data|Materials?)",
        r"^(\d+\.?\s+)(Results?|Findings|Analysis)",
        r"^(\d+\.?\s+)(Discussion|Conclusions?|Summary)",
        r"^(\d+\.?\s+)(References?|Bibliography)",
        r"^(\d+\.?\s+)(Appendix|Appendices)",
        # Roman numerals: "I. Introduction"
        r"^([IVXLC]+\.?\s+)(Introduction|Methods?|Results?|Discussion|Conclusions?)",
        # Unnumbered common sections
        r"^(Abstract)$",
        r"^(Introduction)$",
        r"^(Methods?|Methodology)$",
        r"^(Data and Methods?)$",
        r"^(Results?)$",
        r"^(Discussion)$",
        r"^(Conclusions?)$",
        r"^(References?|Bibliography)$",
    ]

    # Abstract detection patterns
    ABSTRACT_PATTERNS = [
        r"(?:^|\n)Abstract[:\s]*\n(.+?)(?=\n\s*\n|\nIntroduction|\n1\.)",
        r"(?:^|\n)ABSTRACT[:\s]*\n(.+?)(?=\n\s*\n|\nINTRODUCTION|\n1\.)",
    ]

    def __init__(self, use_cache: bool = True):
        """Initialize the indexer.

        Args:
            use_cache: Whether to use caching.
        """
        self.use_cache = use_cache
        self.cache = get_cache() if use_cache else None
        self.chapter_splitter = ChapterSplitter()

    def index(
        self,
        pdf_path: Path,
        doc_type: Optional[Literal["paper", "book"]] = None,
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
        if self.use_cache and not force:
            cached = self.cache.get_index(pdf_path)
            if cached:
                return self._dict_to_index(cached)

        # Build index
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        # Auto-detect type if not specified
        if doc_type is None:
            doc_type = self._detect_type(reader, total_pages)

        # Create base index
        doc_id = file_hash(pdf_path)
        index = DocumentIndex(
            id=doc_id,
            file=str(pdf_path.name),
            pages=total_pages,
            type=doc_type,
        )

        # Extract metadata
        self._extract_metadata(reader, index)

        # Extract structure based on type
        if doc_type == "book":
            self._index_book(pdf_path, reader, index)
        else:
            self._index_paper(reader, index)

        # Extract tables and figures info
        self._detect_tables(pdf_path, index)
        self._count_references(reader, index)

        # Cache result
        if self.use_cache:
            self.cache.set_index(pdf_path, index.to_dict())

        return index

    def _detect_type(self, reader: PdfReader, total_pages: int) -> Literal["paper", "book"]:
        """Auto-detect document type.

        Heuristics:
        - Books typically have 50+ pages
        - Books have chapter patterns or bookmarks
        - Papers typically have abstract + numbered sections
        """
        # Check page count
        if total_pages >= 50:
            # Check for chapter patterns
            chapters = self.chapter_splitter.detect_chapters.__wrapped__(
                self.chapter_splitter, Path("dummy")
            ) if hasattr(self.chapter_splitter.detect_chapters, '__wrapped__') else []

            # Actually check via bookmarks
            if reader.outline:
                return "book"

            # Check first few pages for chapter patterns
            for page_num in range(min(5, total_pages)):
                text = reader.pages[page_num].extract_text() or ""
                for pattern in self.chapter_splitter.CHAPTER_PATTERNS:
                    if re.search(pattern, text[:500], re.MULTILINE):
                        return "book"

        return "paper"

    def _extract_metadata(self, reader: PdfReader, index: DocumentIndex) -> None:
        """Extract document metadata."""
        # Try PDF metadata first
        if reader.metadata:
            if reader.metadata.title:
                index.title = reader.metadata.title
            if reader.metadata.author:
                index.authors = [reader.metadata.author]

        # Try to extract from first page
        if not index.title and reader.pages:
            first_page_text = reader.pages[0].extract_text() or ""
            lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]

            # Title is usually the first non-empty line that's substantial
            for line in lines[:5]:
                if len(line) > 10 and not line.startswith("http"):
                    index.title = line[:200]  # Truncate long titles
                    break

        # Extract abstract
        if reader.pages:
            first_pages_text = ""
            for i in range(min(3, len(reader.pages))):
                first_pages_text += (reader.pages[i].extract_text() or "") + "\n"

            for pattern in self.ABSTRACT_PATTERNS:
                match = re.search(pattern, first_pages_text, re.DOTALL | re.IGNORECASE)
                if match:
                    abstract = match.group(1).strip()
                    # Clean up and truncate
                    abstract = re.sub(r'\s+', ' ', abstract)
                    if len(abstract) > 1000:
                        abstract = abstract[:1000] + "..."
                    index.abstract = abstract
                    break

    def _index_paper(self, reader: PdfReader, index: DocumentIndex) -> None:
        """Index a paper document (detect sections)."""
        sections = []
        section_id = 0

        compiled_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self.SECTION_PATTERNS
        ]

        section_starts = []  # (page_num, title)

        for page_num in range(len(reader.pages)):
            text = reader.pages[page_num].extract_text() or ""
            lines = text.split("\n")

            for line in lines[:20]:  # Check first 20 lines of each page
                line = line.strip()
                for pattern in compiled_patterns:
                    if pattern.match(line):
                        # Found a section header
                        title = line[:100]  # Truncate
                        section_starts.append((page_num, title))
                        break

        # Convert to sections with page ranges
        for i, (page_num, title) in enumerate(section_starts):
            section_id += 1
            end_page = (
                section_starts[i + 1][0]
                if i + 1 < len(section_starts)
                else len(reader.pages)
            )

            sections.append(Section(
                id=section_id,
                title=title,
                pages=(page_num + 1, end_page),  # 1-indexed
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
        """Detect tables in the document."""
        import pdfplumber

        tables = []
        table_id = 0

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.find_tables()
                    for _ in page_tables:
                        table_id += 1
                        tables.append(TableInfo(
                            id=table_id,
                            page=page_num + 1,  # 1-indexed
                            caption=None,  # Would need more complex logic to extract
                        ))
        except Exception:
            pass  # Skip table detection on error

        index.tables = tables

    def _count_references(self, reader: PdfReader, index: DocumentIndex) -> None:
        """Count references in the document."""
        # Look for references section in last few pages
        refs_count = 0

        for page_num in range(max(0, len(reader.pages) - 5), len(reader.pages)):
            text = reader.pages[page_num].extract_text() or ""

            # Check if this is a references page
            if re.search(r'^(References?|Bibliography)', text, re.IGNORECASE | re.MULTILINE):
                # Count reference entries (lines starting with [ or numbers)
                refs_count += len(re.findall(r'^\s*\[?\d+[\.\])]', text, re.MULTILINE))
                # Also count author-year style
                refs_count += len(re.findall(r'^[A-Z][a-z]+,?\s+[A-Z]', text, re.MULTILINE))

        index.refs_count = refs_count

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
