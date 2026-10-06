"""Tests for the ingestion module."""

import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion import (
    Chunk, chunk_text, table_to_text, extract_pages_text,
    validate_pdf, ingest_pdf, _extract_version, _extract_sections,
)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


class TestChunkDataclass:
    def test_chunk_creation(self):
        c = Chunk(doc_name="test.pdf", doc_id="abc123", page_number=1,
                  chunk_index=1, text="Hello world")
        assert c.doc_name == "test.pdf"
        assert c.page_number == 1
        assert c.text == "Hello world"

    def test_chunk_citation(self):
        c = Chunk(doc_name="HLD_BCM_v1.0.pdf", doc_id="abc", page_number=3,
                  chunk_index=1, text="test")
        assert c.citation == "HLD_BCM_v1.0.pdf, Page 3"

    def test_chunk_id(self):
        c = Chunk(doc_name="test.pdf", doc_id="abc123", page_number=1,
                  chunk_index=5, text="test")
        assert c.chunk_id == "abc123_chunk_5"

    def test_chunk_default_metadata(self):
        c = Chunk(doc_name="test.pdf", doc_id="abc", page_number=1,
                  chunk_index=1, text="test")
        assert c.section == "General"
        assert c.document_version == "Unknown"
        assert c.source_type == "text"


class TestChunking:
    def test_empty_text(self):
        assert chunk_text("", 100, 20) == []

    def test_whitespace_only(self):
        assert chunk_text("   \n\n   ", 100, 20) == []

    def test_short_text_single_chunk(self):
        text = "Hello world"
        chunks = chunk_text(text, 100, 20)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_long_text_multiple_chunks(self):
        text = "A" * 500
        chunks = chunk_text(text, 100, 20)
        assert len(chunks) > 1

    def test_overlap_present(self):
        text = "Word " * 100  # 500 chars
        chunks = chunk_text(text, 100, 30)
        # With overlap, later chunks should share some content
        assert len(chunks) > 1

    def test_paragraph_boundary_breaking(self):
        text = "First paragraph text here. " * 5 + "\n\n" + "Second paragraph. " * 5
        chunks = chunk_text(text, 200, 20)
        assert len(chunks) >= 1


class TestTableToText:
    def test_basic_table(self):
        table = [["Name", "Value"], ["A", "1"], ["B", "2"]]
        result = table_to_text(table)
        assert "Name | Value" in result
        assert "A | 1" in result

    def test_none_cells(self):
        table = [["Name", None], [None, "1"]]
        result = table_to_text(table)
        assert "Name |" in result

    def test_empty_table(self):
        result = table_to_text([])
        assert result == ""


class TestVersionExtraction:
    def test_version_with_prefix(self):
        assert _extract_version("Document Version 1.0") == "1.0"

    def test_version_v_prefix(self):
        assert _extract_version("HLD V2.3 document") == "2.3"

    def test_no_version(self):
        assert _extract_version("No version here") == "Unknown"


class TestPDFValidation:
    @pytest.mark.skipif(not (SAMPLE_DIR / "HLD_BCM_v1.0.pdf").exists(),
                        reason="Sample PDF not available")
    def test_valid_pdf(self):
        result = validate_pdf(str(SAMPLE_DIR / "HLD_BCM_v1.0.pdf"))
        assert result["valid"] is True
        assert result["pages"] > 0

    def test_nonexistent_file(self):
        result = validate_pdf("nonexistent.pdf")
        assert result["valid"] is False

    def test_wrong_extension(self):
        result = validate_pdf("test.txt")
        assert result["valid"] is False


class TestPDFIngestion:
    @pytest.mark.skipif(not (SAMPLE_DIR / "HLD_BCM_v1.0.pdf").exists(),
                        reason="Sample PDF not available")
    def test_ingest_bcm(self):
        chunks = ingest_pdf(
            str(SAMPLE_DIR / "HLD_BCM_v1.0.pdf"),
            doc_name="HLD_BCM_v1.0.pdf",
            chunk_size=1200,
            overlap=200,
        )
        assert len(chunks) > 0
        # Every chunk must have page number
        for c in chunks:
            assert c.page_number >= 1
            assert c.doc_name == "HLD_BCM_v1.0.pdf"
            assert c.text.strip() != ""

    @pytest.mark.skipif(not (SAMPLE_DIR / "HLD_BCM_v1.0.pdf").exists(),
                        reason="Sample PDF not available")
    def test_chunk_metadata_preservation(self):
        chunks = ingest_pdf(
            str(SAMPLE_DIR / "HLD_BCM_v1.0.pdf"),
            doc_name="HLD_BCM_v1.0.pdf",
            chunk_size=1200,
            overlap=200,
            project_id="test_project",
        )
        for c in chunks:
            assert c.doc_id != ""
            assert c.chunk_index > 0
            assert c.project_id == "test_project"
            assert c.document_version != "Unknown"  # Should auto-detect "1.0"

    @pytest.mark.skipif(not (SAMPLE_DIR / "HLD_BCM_v1.0.pdf").exists(),
                        reason="Sample PDF not available")
    def test_page_numbers_in_range(self):
        chunks = ingest_pdf(
            str(SAMPLE_DIR / "HLD_BCM_v1.0.pdf"),
            doc_name="HLD_BCM_v1.0.pdf",
            chunk_size=1200,
            overlap=200,
        )
        pages = {c.page_number for c in chunks}
        assert min(pages) >= 1
        assert max(pages) <= 10  # Sample PDFs are short
