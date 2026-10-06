"""
Vector store module.

Wraps a local FAISS index per "collection" (project workspace). Each
collection is persisted to disk as:
    data/vector_store/<collection_name>/index.faiss
    data/vector_store/<collection_name>/chunks.pkl

Provides project isolation matching the case-study requirement.
"""

import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Optional

import faiss
import numpy as np

import config
from src.ingestion import Chunk
from src.embeddings import embed_texts, embed_query

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-backed vector store with per-project persistence."""

    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.dir_path = config.VECTOR_STORE_DIR / collection_name
        self.dir_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir_path / "index.faiss"
        self.chunks_path = self.dir_path / "chunks.pkl"

        self.index: Optional[faiss.Index] = None
        self.chunks: List[Chunk] = []

        self._load()

    def _load(self):
        """Load existing index and chunks from disk, or create empty ones."""
        if self.index_path.exists() and self.chunks_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.chunks_path, "rb") as f:
                    self.chunks = pickle.load(f)
                logger.info(f"Loaded collection '{self.collection_name}': "
                          f"{self.index.ntotal} vectors, {len(self.chunks)} chunks")
            except Exception as e:
                logger.error(f"Error loading collection '{self.collection_name}': {e}")
                self.index = faiss.IndexFlatIP(config.EMBEDDING_DIM)
                self.chunks = []
        else:
            self.index = faiss.IndexFlatIP(config.EMBEDDING_DIM)
            self.chunks = []

    def _save(self):
        """Persist index and chunks to disk."""
        try:
            faiss.write_index(self.index, str(self.index_path))
            with open(self.chunks_path, "wb") as f:
                pickle.dump(self.chunks, f)
        except Exception as e:
            logger.error(f"Error saving collection '{self.collection_name}': {e}")
            raise

    def add_chunks(self, chunks: List[Chunk]):
        """Embed and add a list of Chunk objects to this collection's index."""
        if not chunks:
            return
        texts = [c.text for c in chunks]
        vectors = embed_texts(texts)
        self.index.add(vectors)
        self.chunks.extend(chunks)
        self._save()
        logger.info(f"Added {len(chunks)} chunks to '{self.collection_name}'")

    def search(
        self,
        query: str,
        top_k: int = None,
        doc_filter: Optional[str] = None,
    ) -> List[Tuple[Chunk, float]]:
        """
        Return the top_k most similar chunks to the query, with similarity scores.
        Optionally filter by document name.
        """
        if self.index is None or self.index.ntotal == 0:
            return []
        top_k = top_k or config.TOP_K_RETRIEVAL

        if doc_filter:
            # Search more broadly, then filter
            search_k = min(top_k * 5, self.index.ntotal)
        else:
            search_k = min(top_k, self.index.ntotal)

        query_vec = embed_query(query)
        scores, indices = self.index.search(query_vec, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = self.chunks[idx]
            if doc_filter and chunk.doc_name != doc_filter:
                continue
            results.append((chunk, float(score)))
            if len(results) >= top_k:
                break

        return results

    def document_names(self) -> List[str]:
        """Return sorted list of unique document names in this collection."""
        return sorted({c.doc_name for c in self.chunks})

    def chunks_for_document(self, doc_name: str) -> List[Chunk]:
        """Return all chunks for a specific document."""
        return [c for c in self.chunks if c.doc_name == doc_name]

    def is_empty(self) -> bool:
        """Check if the index has any vectors."""
        return self.index is None or self.index.ntotal == 0

    def has_document(self, doc_name: str) -> bool:
        """Check if a document is already indexed."""
        return doc_name in self.document_names()

    def remove_document(self, doc_name: str):
        """Remove all chunks for a document and rebuild the index."""
        remaining = [c for c in self.chunks if c.doc_name != doc_name]
        if len(remaining) == len(self.chunks):
            return  # Document not found

        self.chunks = remaining
        # Rebuild index
        self.index = faiss.IndexFlatIP(config.EMBEDDING_DIM)
        if self.chunks:
            texts = [c.text for c in self.chunks]
            vectors = embed_texts(texts)
            self.index.add(vectors)
        self._save()
        logger.info(f"Removed document '{doc_name}' from '{self.collection_name}'")

    def stats(self) -> dict:
        """Return statistics about this collection."""
        docs = self.document_names()
        doc_details = {}
        for d in docs:
            doc_chunks = self.chunks_for_document(d)
            pages = sorted({c.page_number for c in doc_chunks})
            doc_details[d] = {
                "chunks": len(doc_chunks),
                "pages": len(pages),
                "version": doc_chunks[0].document_version if doc_chunks else "Unknown",
            }

        return {
            "collection": self.collection_name,
            "total_chunks": len(self.chunks),
            "total_documents": len(docs),
            "documents": docs,
            "document_details": doc_details,
        }

    @staticmethod
    def list_collections() -> List[str]:
        """List all available project collections."""
        if not config.VECTOR_STORE_DIR.exists():
            return []
        return sorted(
            p.name for p in config.VECTOR_STORE_DIR.iterdir()
            if p.is_dir() and (p / "index.faiss").exists()
        )

    @staticmethod
    def delete_collection(collection_name: str):
        """Delete a collection and all its data."""
        import shutil
        col_path = config.VECTOR_STORE_DIR / collection_name
        if col_path.exists():
            shutil.rmtree(col_path)
            logger.info(f"Deleted collection '{collection_name}'")
