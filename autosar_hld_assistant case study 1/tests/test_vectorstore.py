"""Tests for the vector store module."""

import sys
import shutil
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src.ingestion import Chunk
from src.vectorstore import VectorStore


TEST_COLLECTION = "_test_collection_pytest"


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test collection before and after each test."""
    col_path = config.VECTOR_STORE_DIR / TEST_COLLECTION
    if col_path.exists():
        shutil.rmtree(col_path)
    yield
    if col_path.exists():
        shutil.rmtree(col_path)


def _make_chunks(n=3, doc_name="test.pdf"):
    return [
        Chunk(
            doc_name=doc_name,
            doc_id="test123",
            page_number=i + 1,
            chunk_index=i + 1,
            text=f"This is test chunk number {i + 1} about AUTOSAR components and interfaces.",
        )
        for i in range(n)
    ]


class TestVectorStoreBasic:
    def test_create_empty_store(self):
        store = VectorStore(TEST_COLLECTION)
        assert store.is_empty()
        assert store.document_names() == []

    def test_add_chunks(self):
        store = VectorStore(TEST_COLLECTION)
        chunks = _make_chunks(3)
        store.add_chunks(chunks)
        assert not store.is_empty()
        assert len(store.chunks) == 3

    def test_persistence(self):
        # Add chunks to one instance
        store1 = VectorStore(TEST_COLLECTION)
        store1.add_chunks(_make_chunks(3))

        # Load from a new instance
        store2 = VectorStore(TEST_COLLECTION)
        assert not store2.is_empty()
        assert len(store2.chunks) == 3

    def test_document_names(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(2, "doc_a.pdf"))
        store.add_chunks(_make_chunks(2, "doc_b.pdf"))
        names = store.document_names()
        assert "doc_a.pdf" in names
        assert "doc_b.pdf" in names

    def test_chunks_for_document(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(2, "doc_a.pdf"))
        store.add_chunks(_make_chunks(3, "doc_b.pdf"))
        assert len(store.chunks_for_document("doc_a.pdf")) == 2
        assert len(store.chunks_for_document("doc_b.pdf")) == 3

    def test_has_document(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(2, "doc_a.pdf"))
        assert store.has_document("doc_a.pdf")
        assert not store.has_document("nonexistent.pdf")


class TestVectorStoreSearch:
    def test_search_returns_results(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(5))
        results = store.search("AUTOSAR components", top_k=3)
        assert len(results) > 0
        assert len(results) <= 3
        # Each result is (chunk, score) tuple
        for chunk, score in results:
            assert isinstance(chunk, Chunk)
            assert isinstance(score, float)

    def test_search_empty_store(self):
        store = VectorStore(TEST_COLLECTION)
        results = store.search("test query")
        assert results == []

    def test_search_with_doc_filter(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(3, "doc_a.pdf"))
        store.add_chunks(_make_chunks(3, "doc_b.pdf"))

        results = store.search("AUTOSAR", top_k=5, doc_filter="doc_a.pdf")
        for chunk, score in results:
            assert chunk.doc_name == "doc_a.pdf"


class TestVectorStoreRemoval:
    def test_remove_document(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(3, "doc_a.pdf"))
        store.add_chunks(_make_chunks(3, "doc_b.pdf"))

        store.remove_document("doc_a.pdf")
        assert not store.has_document("doc_a.pdf")
        assert store.has_document("doc_b.pdf")
        assert len(store.chunks) == 3

    def test_remove_nonexistent_document(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(3))
        store.remove_document("nonexistent.pdf")
        assert len(store.chunks) == 3  # No change


class TestVectorStoreStats:
    def test_stats(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(3, "test.pdf"))
        stats = store.stats()
        assert stats["collection"] == TEST_COLLECTION
        assert stats["total_chunks"] == 3
        assert stats["total_documents"] == 1
        assert "test.pdf" in stats["documents"]


class TestVectorStoreCollections:
    def test_list_collections(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(1))
        collections = VectorStore.list_collections()
        assert TEST_COLLECTION in collections

    def test_delete_collection(self):
        store = VectorStore(TEST_COLLECTION)
        store.add_chunks(_make_chunks(1))
        VectorStore.delete_collection(TEST_COLLECTION)
        assert TEST_COLLECTION not in VectorStore.list_collections()
