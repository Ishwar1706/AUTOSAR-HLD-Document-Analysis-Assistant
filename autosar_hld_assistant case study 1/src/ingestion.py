"""
Ingestion module.

Responsible for:
- Extracting text (and tables, where present) from an uploaded PDF, page by page
- Section-aware, page-aware chunking with overlap
- Attaching rich metadata (document name, page number, section, chunk ID, version)
  to every chunk for reliable citation tracking.
"""

import re
import uuid
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path

import pymupdf  # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a single text chunk from a parsed PDF document."""
    doc_name: str
    doc_id: str
    page_number: int
    chunk_index: int
    text: str
    section: str = "General"
    document_version: str = "Unknown"
    source_type: str = "text"
    project_id: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def citation(self) -> str:
        return f"{self.doc_name}, Page {self.page_number}"

    @property
    def chunk_id(self) -> str:
        return f"{self.doc_id}_chunk_{self.chunk_index}"


def _extract_version(text: str) -> str:
    """Try to extract a version number from document text."""
    patterns = [
        r'Version\s+(\d+\.\d+)',
        r'V(\d+\.\d+)',
        r'v(\d+\.\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "Unknown"


def _extract_sections(text: str) -> List[dict]:
    """
    Identify section headings in the text.
    Returns a list of dicts with 'title' and 'start_pos' keys.
    """
    section_patterns = [
        r'^(#{1,4}\s+.+)$',
        r'^(\d+\.\s+.+)$',
        r'^([A-Z][A-Za-z\s]+(?:and|&)\s+[A-Za-z\s]+)$',
        r'^(Introduction and Scope)$',
        r'^(Software Component Overview)$',
        r'^(Ports and Interfaces)$',
        r'^(Signals and Data Elements)$',
        r'^(Component Dependencies)$',
        r'^(Functional Flow.+)$',
        r'^(Assumptions and Open Points)$',
        r'^(Change Summary.+)$',
        r'^(Revision History)$',
        r'^(Document Control)$',
        r'^(Safety-Relevant Notes)$',
    ]

    sections = []
    for line_start in range(len(text)):
        if line_start > 0 and text[line_start - 1] != '\n':
            continue
        line_end = text.find('\n', line_start)
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end].strip()
        if not line or len(line) > 100:
            continue
        for pattern in section_patterns:
            if re.match(pattern, line, re.MULTILINE):
                sections.append({'title': line, 'start_pos': line_start})
                break

    return sections


def extract_pages_text(pdf_path: str) -> List[str]:
    """
    Extract raw text from every page of a PDF using PyMuPDF.
    Falls back gracefully to an empty string for pages that fail to parse.
    """
    pages_text = []
    try:
        with pymupdf.open(pdf_path) as doc:
            for page in doc:
                try:
                    text = page.get_text("text")
                except Exception:
                    text = ""
                pages_text.append(text or "")
    except Exception as e:
        logger.error(f"Failed to open PDF {pdf_path}: {e}")
        raise ValueError(f"Cannot read PDF file: {e}")

    if not pages_text:
        raise ValueError("PDF contains no pages or could not be read.")

    return pages_text


def extract_tables(pdf_path: str) -> Dict[int, list]:
    """
    Extract tables per page using pdfplumber.
    Returns: { page_number (1-indexed): [table_as_list_of_rows, ...] }
    """
    tables_by_page = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    tables = page.extract_tables()
                except Exception:
                    tables = []
                if tables:
                    tables_by_page[i] = tables
    except Exception as e:
        logger.warning(f"Table extraction failed for {pdf_path}: {e}")
    return tables_by_page


def table_to_text(table: List[List[str]]) -> str:
    """Flatten a table (list of rows) into a readable pipe-delimited text block."""
    lines = []
    for row in table:
        clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
        lines.append(" | ".join(clean_row))
    return "\n".join(lines)


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Sliding-window chunker over characters, breaking preferentially
    on paragraph/sentence boundaries where possible.
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)

        # Try to break on a paragraph or sentence boundary near the end
        if end < length:
            window = text[start:end]
            break_point = max(window.rfind("\n\n"), window.rfind(". "))
            if break_point > chunk_size * 0.5:
                end = start + break_point + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= length:
            break
        start = max(end - overlap, start + 1)

    return chunks


def _get_section_for_position(sections: list, position: int, total_length: int) -> str:
    """Determine which section a given text position falls into."""
    if not sections:
        return "General"

    current_section = "General"
    for sec in sections:
        if sec['start_pos'] <= position:
            current_section = sec['title']
        else:
            break
    return current_section


def validate_pdf(pdf_path: str) -> Dict:
    """Validate a PDF file before ingestion. Returns status dict."""
    path = Path(pdf_path)

    if not path.exists():
        return {"valid": False, "error": "File not found"}

    if path.suffix.lower() != '.pdf':
        return {"valid": False, "error": "Not a PDF file"}

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 50:
        return {"valid": False, "error": f"File too large ({size_mb:.1f} MB > 50 MB limit)"}

    try:
        with pymupdf.open(pdf_path) as doc:
            page_count = len(doc)
            if page_count == 0:
                return {"valid": False, "error": "PDF has no pages"}
            # Check if any page has text
            has_text = any(page.get_text("text").strip() for page in doc)
            if not has_text:
                return {"valid": True, "warning": "PDF appears to be scanned (no extractable text). Content extraction may be limited.", "pages": page_count}
    except Exception as e:
        return {"valid": False, "error": f"Cannot read PDF: {e}"}

    return {"valid": True, "pages": page_count, "size_mb": round(size_mb, 2)}


def ingest_pdf(
    pdf_path: str,
    doc_name: str,
    chunk_size: int,
    overlap: int,
    project_id: str = "",
    document_version: Optional[str] = None,
) -> List[Chunk]:
    """
    Full ingestion pipeline for one PDF:
    1. Validate the PDF
    2. Extract per-page text
    3. Extract per-page tables and append as readable text
    4. Detect document version
    5. Identify sections for section-aware chunking
    6. Chunk each page's combined content
    7. Return a flat list of Chunk objects with full citation metadata
    """
    validation = validate_pdf(pdf_path)
    if not validation.get("valid", False):
        raise ValueError(validation.get("error", "Invalid PDF"))

    pages_text = extract_pages_text(pdf_path)
    tables_by_page = extract_tables(pdf_path)

    # Generate a unique document ID
    doc_id = str(uuid.uuid4())[:8]

    # Auto-detect version from first 2 pages if not provided
    if document_version is None:
        first_pages = " ".join(pages_text[:2])
        document_version = _extract_version(first_pages)

    all_chunks: List[Chunk] = []
    chunk_counter = 0

    for page_idx, page_text in enumerate(pages_text, start=1):
        combined = page_text

        # Append tables as readable text
        if page_idx in tables_by_page:
            for table in tables_by_page[page_idx]:
                table_text = table_to_text(table)
                if table_text.strip():
                    combined += f"\n\n[TABLE ON PAGE {page_idx}]\n{table_text}"

        # Detect sections on this page
        sections = _extract_sections(combined)

        page_chunks = chunk_text(combined, chunk_size, overlap)

        for local_idx, chunk_str in enumerate(page_chunks):
            chunk_counter += 1

            # Determine which section this chunk belongs to
            chunk_start_in_combined = combined.find(chunk_str[:50])
            section = _get_section_for_position(sections, max(0, chunk_start_in_combined), len(combined))

            # Determine source type
            source_type = "text"
            if "[TABLE ON PAGE" in chunk_str:
                source_type = "text+table"

            all_chunks.append(
                Chunk(
                    doc_name=doc_name,
                    doc_id=doc_id,
                    page_number=page_idx,
                    chunk_index=chunk_counter,
                    text=chunk_str,
                    section=section,
                    document_version=document_version,
                    source_type=source_type,
                    project_id=project_id,
                    metadata={
                        "local_index_on_page": local_idx,
                        "has_table": "[TABLE ON PAGE" in chunk_str,
                    },
                )
            )

    logger.info(f"Ingested {doc_name}: {len(all_chunks)} chunks from {len(pages_text)} pages")
    return all_chunks


def get_full_text(pdf_path: str) -> str:
    """Return the full concatenated text of a PDF (used for whole-document entity extraction)."""
    pages_text = extract_pages_text(pdf_path)
    return "\n\n".join(pages_text)


def get_page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF."""
    try:
        with pymupdf.open(pdf_path) as doc:
            return len(doc)
    except Exception:
        return 0
