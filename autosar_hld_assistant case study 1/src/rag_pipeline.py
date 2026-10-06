"""
RAG (Retrieval-Augmented Generation) pipeline.

Implements the core "Natural language question answering with citations"
capability:
1. Retrieve the most relevant chunks for a user query from the vector store
2. Build a prompt restricting the LLM strictly to retrieved context
3. Ask the LLM to answer with inline citations (document + page)
4. Return the answer alongside source chunks and evidence metadata
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.vectorstore import VectorStore
from src.ingestion import Chunk
from src.llm_client import chat_completion, LLMError
from src.prompts import get_rag_prompt, get_summary_prompt

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Result of a RAG query, including answer, sources, and metadata."""
    answer: str
    sources: List[Chunk]
    scores: List[float] = field(default_factory=list)
    num_chunks_retrieved: int = 0
    latency_seconds: float = 0.0
    grounded: bool = True

    @property
    def evidence_summary(self) -> str:
        """Generate a formatted evidence summary."""
        if not self.sources:
            return "No sources retrieved."
        citations = []
        seen = set()
        for c in self.sources:
            key = (c.doc_name, c.page_number)
            if key not in seen:
                seen.add(key)
                citations.append(f"- {c.doc_name} — Page {c.page_number}")
        return "\n".join(citations)


def build_context_block(chunks: List[Chunk]) -> str:
    """Build a formatted context block from retrieved chunks."""
    blocks = []
    for c in chunks:
        blocks.append(
            f"--- [Source: {c.doc_name}, Page {c.page_number}] ---\n{c.text}"
        )
    return "\n\n".join(blocks)


def answer_question(
    collection_name: str,
    question: str,
    top_k: int = None,
    doc_filter: Optional[str] = None,
) -> RAGResult:
    """
    Full RAG pipeline: retrieve → build context → LLM → grounded answer.
    """
    start_time = time.time()
    store = VectorStore(collection_name)

    if store.is_empty():
        return RAGResult(
            answer="No documents have been ingested into this project yet. "
                   "Please upload and process an HLD document first.",
            sources=[],
            grounded=False,
        )

    # Retrieve relevant chunks
    retrieved = store.search(question, top_k=top_k, doc_filter=doc_filter)
    chunks = [c for c, score in retrieved]
    scores = [score for c, score in retrieved]

    if not chunks:
        return RAGResult(
            answer="No relevant content found in the indexed documents for this query.",
            sources=[],
            grounded=False,
        )

    # Check if scores are low (weak evidence)
    avg_score = sum(scores) / len(scores) if scores else 0
    is_grounded = avg_score > 0.3  # Threshold for meaningful similarity

    # Build context and query the LLM
    context_block = build_context_block(chunks)
    user_prompt = f"CONTEXT:\n{context_block}\n\nQUESTION:\n{question}"

    try:
        system_prompt = get_rag_prompt()
        answer = chat_completion(system_prompt, user_prompt)
    except LLMError as e:
        return RAGResult(
            answer=f"LLM service unavailable: {e}",
            sources=chunks,
            scores=scores,
            num_chunks_retrieved=len(chunks),
            latency_seconds=time.time() - start_time,
            grounded=False,
        )

    elapsed = time.time() - start_time

    return RAGResult(
        answer=answer,
        sources=chunks,
        scores=scores,
        num_chunks_retrieved=len(chunks),
        latency_seconds=elapsed,
        grounded=is_grounded,
    )


def summarize_document(collection_name: str, doc_name: str) -> RAGResult:
    """Generate a cited high-level summary of a single ingested document."""
    start_time = time.time()
    store = VectorStore(collection_name)
    chunks = store.chunks_for_document(doc_name)

    if not chunks:
        return RAGResult(
            answer="Document not found in this project.",
            sources=[],
            grounded=False,
        )

    # Cap context size for very large documents by taking a spread of chunks
    max_chunks_for_summary = 25
    if len(chunks) > max_chunks_for_summary:
        step = len(chunks) // max_chunks_for_summary
        chunks = chunks[::step][:max_chunks_for_summary]

    context_block = build_context_block(chunks)
    user_prompt = (
        f"CONTEXT:\n{context_block}\n\n"
        "TASK:\nProvide a structured summary of this HLD document covering: "
        "(1) Purpose and Scope, (2) Main software components, (3) Key interfaces, "
        "(4) Key signals, (5) Dependencies, (6) Functional flows, "
        "(7) Important design points, (8) Open points / missing information. "
        "Cite sources for each point."
    )

    try:
        system_prompt = get_summary_prompt()
        answer = chat_completion(system_prompt, user_prompt)
    except LLMError as e:
        return RAGResult(
            answer=f"LLM service unavailable: {e}",
            sources=chunks,
            latency_seconds=time.time() - start_time,
            grounded=False,
        )

    elapsed = time.time() - start_time

    return RAGResult(
        answer=answer,
        sources=chunks,
        num_chunks_retrieved=len(chunks),
        latency_seconds=elapsed,
        grounded=True,
    )
