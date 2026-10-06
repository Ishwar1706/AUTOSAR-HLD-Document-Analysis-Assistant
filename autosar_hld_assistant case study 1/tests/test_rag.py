"""Tests for RAG pipeline components and evaluation."""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag_pipeline import build_context_block, RAGResult
from src.ingestion import Chunk
from src.evaluation import (
    evaluate_retrieval_recall,
    evaluate_answer_groundedness,
    evaluate_extraction_precision_recall,
)


class TestBuildContextBlock:
    def test_single_chunk(self):
        chunks = [Chunk(doc_name="test.pdf", doc_id="a", page_number=1,
                        chunk_index=1, text="Hello world")]
        result = build_context_block(chunks)
        assert "[Source: test.pdf, Page 1]" in result
        assert "Hello world" in result

    def test_multiple_chunks(self):
        chunks = [
            Chunk(doc_name="a.pdf", doc_id="a", page_number=1, chunk_index=1, text="First"),
            Chunk(doc_name="b.pdf", doc_id="b", page_number=3, chunk_index=2, text="Second"),
        ]
        result = build_context_block(chunks)
        assert "[Source: a.pdf, Page 1]" in result
        assert "[Source: b.pdf, Page 3]" in result

    def test_empty_chunks(self):
        result = build_context_block([])
        assert result == ""


class TestRAGResult:
    def test_evidence_summary(self):
        sources = [
            Chunk(doc_name="test.pdf", doc_id="a", page_number=1, chunk_index=1, text="a"),
            Chunk(doc_name="test.pdf", doc_id="a", page_number=3, chunk_index=2, text="b"),
            Chunk(doc_name="test.pdf", doc_id="a", page_number=1, chunk_index=3, text="c"),  # duplicate page
        ]
        result = RAGResult(answer="test", sources=sources)
        summary = result.evidence_summary
        assert "test.pdf" in summary
        assert "Page 1" in summary
        assert "Page 3" in summary
        # Should deduplicate
        assert summary.count("Page 1") == 1

    def test_empty_sources(self):
        result = RAGResult(answer="test", sources=[])
        assert "No sources" in result.evidence_summary


class TestRetrievalRecall:
    def test_perfect_recall(self):
        assert evaluate_retrieval_recall([1, 2, 3], [1, 2, 3]) == 1.0

    def test_partial_recall(self):
        assert evaluate_retrieval_recall([1, 2], [1, 2, 3]) == pytest.approx(2/3)

    def test_no_recall(self):
        assert evaluate_retrieval_recall([4, 5], [1, 2, 3]) == 0.0

    def test_empty_expected(self):
        assert evaluate_retrieval_recall([1, 2], []) == 1.0

    def test_empty_retrieved(self):
        assert evaluate_retrieval_recall([], [1, 2]) == 0.0

    def test_superset_retrieval(self):
        assert evaluate_retrieval_recall([1, 2, 3, 4, 5], [2, 3]) == 1.0


class TestAnswerGroundedness:
    def test_all_points_found(self):
        answer = "The system uses SWC_DoorLockControl and DoorLockCmd signal."
        points = ["SWC_DoorLockControl", "DoorLockCmd"]
        result = evaluate_answer_groundedness(answer, points)
        assert result["score"] == 1.0
        assert result["matched"] == 2

    def test_partial_match(self):
        answer = "The system uses SWC_DoorLockControl."
        points = ["SWC_DoorLockControl", "DoorLockCmd"]
        result = evaluate_answer_groundedness(answer, points)
        assert result["score"] == 0.5

    def test_no_match(self):
        answer = "The system is complex."
        points = ["SWC_DoorLockControl", "DoorLockCmd"]
        result = evaluate_answer_groundedness(answer, points)
        assert result["score"] == 0.0

    def test_empty_points(self):
        result = evaluate_answer_groundedness("any answer", [])
        assert result["score"] == 1.0

    def test_case_insensitive(self):
        answer = "swc_doorlockcontrol is used."
        points = ["SWC_DoorLockControl"]
        result = evaluate_answer_groundedness(answer, points)
        assert result["score"] == 1.0


class TestExtractionMetrics:
    def test_perfect_extraction(self):
        result = evaluate_extraction_precision_recall(
            ["SWC_A", "SWC_B"], ["SWC_A", "SWC_B"]
        )
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0
        assert result["f1"] == 1.0

    def test_partial_extraction(self):
        result = evaluate_extraction_precision_recall(
            ["SWC_A", "SWC_B", "SWC_C"], ["SWC_A", "SWC_B"]
        )
        assert result["recall"] == 1.0
        assert result["precision"] < 1.0

    def test_missing_items(self):
        result = evaluate_extraction_precision_recall(
            ["SWC_A"], ["SWC_A", "SWC_B", "SWC_C"]
        )
        assert result["precision"] == 1.0
        assert result["recall"] < 1.0

    def test_no_overlap(self):
        result = evaluate_extraction_precision_recall(
            ["SWC_X"], ["SWC_A", "SWC_B"]
        )
        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["f1"] == 0.0

    def test_both_empty(self):
        result = evaluate_extraction_precision_recall([], [])
        assert result["f1"] == 1.0

    def test_case_insensitive(self):
        result = evaluate_extraction_precision_recall(
            ["swc_a", "SWC_B"], ["SWC_A", "swc_b"]
        )
        assert result["recall"] == 1.0
