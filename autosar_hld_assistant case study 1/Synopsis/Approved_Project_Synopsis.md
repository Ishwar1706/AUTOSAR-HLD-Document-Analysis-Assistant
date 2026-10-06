# Project Synopsis

## AUTOSAR HLD Document Analysis Assistant using Retrieval-Augmented Generation

---

### Title
AUTOSAR HLD Document Analysis Assistant using Retrieval-Augmented Generation

### Problem Statement
Automotive engineering teams work with large, unstructured AUTOSAR High-Level Design (HLD) documents that describe software components, interfaces, signals, dependencies, and functional flows. Manual review of these documents is time-consuming, error-prone, and lacks traceability. Engineers must manually search through hundreds of pages to find specific architecture information, compare revisions, and identify inconsistencies.

### Motivation
The rise of Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) presents an opportunity to create AI-assisted tools that help engineers navigate and analyze complex technical documents. By grounding LLM responses in actual document content with citations, RAG systems can provide reliable, traceable answers while mitigating hallucination risks. This project demonstrates this capability specifically for the automotive AUTOSAR domain.

### Objectives
1. Build a document ingestion pipeline for AUTOSAR HLD PDFs with page-level metadata
2. Implement semantic search using local embeddings and FAISS vector database
3. Develop a RAG-based Q&A system with source citations and hallucination controls
4. Extract structured architecture entities (components, interfaces, signals, dependencies)
5. Enable document/revision comparison with change detection
6. Implement architecture consistency review for potential issue identification
7. Create an evaluation framework with benchmark questions and measurable metrics
8. Maintain audit traceability for all AI-assisted operations

### Proposed Methodology
1. **Document Parsing**: Extract text and tables from PDFs using PyMuPDF and pdfplumber
2. **Intelligent Chunking**: Section-aware, page-aware chunking with metadata preservation
3. **Local Embeddings**: Generate 384-dimensional vectors using BAAI/bge-small-en-v1.5
4. **Vector Storage**: FAISS IndexFlatIP with per-project isolation
5. **RAG Pipeline**: Retrieve relevant chunks → assemble context → LLM generation with grounding
6. **Entity Extraction**: Batch LLM extraction with JSON validation and deduplication
7. **Comparison**: Entity-level diffing between document revisions
8. **Evaluation**: 25 benchmark questions with retrieval recall and groundedness metrics

### Technology Stack
- Python 3.10+, Streamlit, Groq API (LLM), BAAI/bge-small-en-v1.5 (embeddings)
- FAISS (vector database), PyMuPDF + pdfplumber (PDF parsing), SQLite (audit)

### Dataset
Three synthetic AUTOSAR HLD PDF documents (BCM, ADAS FCW, BMS) created for pilot evaluation. Not derived from proprietary automotive data.

### Expected Outcomes
- Functional AI assistant for HLD document analysis
- Grounded, cited answers with hallucination resistance
- Structured extraction of architecture entities
- Revision comparison capability
- Measurable evaluation metrics (retrieval recall, groundedness)
- Complete audit traceability

### Scope
**In scope**: PDF ingestion, RAG Q&A, entity extraction, comparison, review, evaluation, export, audit
**Out of scope**: Production deployment, enterprise auth, real automotive data, diagram understanding

### Limitations
- LLM requires external API access
- Synthetic evaluation dataset
- No diagram/image understanding
- Pilot-scale (not enterprise-scale)

### Future Scope
- Local LLM deployment (Ollama)
- Enterprise authentication and PostgreSQL
- Neo4j architecture graph visualization
- Multimodal diagram understanding
- CI/CD integration

### References
1. Lewis et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." NeurIPS.
2. Reimers & Gurevych (2019). "Sentence-BERT." EMNLP.
3. AUTOSAR Classic Platform Methodology. https://www.autosar.org
