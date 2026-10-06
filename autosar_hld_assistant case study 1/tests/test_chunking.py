"""Tests for the chunking functionality."""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion import chunk_text, _extract_sections


class TestChunkTextEdgeCases:
    def test_exact_chunk_size(self):
        text = "A" * 100
        chunks = chunk_text(text, 100, 20)
        assert len(chunks) == 1

    def test_just_over_chunk_size(self):
        text = "A" * 101
        chunks = chunk_text(text, 100, 20)
        assert len(chunks) >= 1

    def test_very_small_chunk_size(self):
        text = "Hello world this is a test"
        chunks = chunk_text(text, 10, 2)
        assert len(chunks) > 1

    def test_overlap_larger_than_chunk(self):
        text = "Hello world this is a test sentence for chunking"
        # Overlap can't be larger than chunk; function handles gracefully
        chunks = chunk_text(text, 20, 15)
        assert len(chunks) >= 1

    def test_sentence_boundary_breaking(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_text(text, 40, 5)
        # Should attempt to break on ". "
        for chunk in chunks:
            assert len(chunk) > 0

    def test_newline_boundary_breaking(self):
        text = "First paragraph\n\nSecond paragraph\n\nThird paragraph"
        chunks = chunk_text(text, 30, 5)
        assert len(chunks) >= 1

    def test_unicode_text(self):
        text = "Temperature is 25°C. Voltage is 3.7V. Current is 10A."
        chunks = chunk_text(text, 30, 5)
        assert len(chunks) >= 1

    def test_special_autosar_content(self):
        text = "SWC_DoorLockControl provides PPort_DoorLockCmd (Sender-Receiver). " * 10
        chunks = chunk_text(text, 200, 50)
        assert len(chunks) >= 1
        # Content should be preserved
        full_text = " ".join(chunks)
        assert "SWC_DoorLockControl" in full_text


class TestSectionExtraction:
    def test_numbered_sections(self):
        text = "1. Introduction and Scope\nSome content here.\n2. Software Component Overview\nMore content."
        sections = _extract_sections(text)
        assert len(sections) >= 1

    def test_known_section_names(self):
        text = "Ports and Interfaces\nSome port descriptions.\nSignals and Data Elements\nSignal list."
        sections = _extract_sections(text)
        titles = [s["title"] for s in sections]
        assert any("Ports and Interfaces" in t for t in titles)

    def test_empty_text(self):
        sections = _extract_sections("")
        assert sections == []

    def test_no_sections(self):
        text = "Just some plain text without any recognizable section headers."
        sections = _extract_sections(text)
        # May or may not find sections, but shouldn't crash
        assert isinstance(sections, list)
