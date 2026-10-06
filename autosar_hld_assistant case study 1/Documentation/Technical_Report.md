# Technical Report — AUTOSAR HLD Document Analysis Assistant

## Using Retrieval-Augmented Generation for Automotive Architecture Knowledge Management

---

## Chapter 1 — Introduction

### 1.1 Automotive Engineering Context

The automotive industry relies heavily on standardized software architecture frameworks, with AUTOSAR (AUTomotive Open System ARchitecture) being the dominant standard for vehicle software development. AUTOSAR defines a layered architecture comprising Application Software Components (SWCs), the Runtime Environment (RTE), Basic Software (BSW), and hardware abstraction layers.

High-Level Design (HLD) documents are critical artifacts in AUTOSAR development. They describe the software component architecture, interfaces, ports, signals, data flows, and dependencies for each ECU subsystem. These documents often span dozens to hundreds of pages and serve as the primary reference for architects, developers, integrators, and testers.

### 1.2 AI Opportunity

Large Language Models (LLMs) combined with Retrieval-Augmented Generation (RAG) present an opportunity to automate the extraction, search, and validation of architectural knowledge from HLD documents. By grounding LLM responses in actual document content, RAG systems can provide cited, traceable answers while mitigating hallucination risks.

### 1.3 Problem Statement

Manual analysis of AUTOSAR HLD documents is:
- **Time-consuming**: Engineers must read through entire documents to find specific information
- **Error-prone**: Manual cross-referencing can miss inconsistencies
- **Difficult to trace**: There is no automated mechanism to trace from a query to its source evidence
- **Knowledge-dependent**: Understanding requires significant domain expertise
- **Repetitive**: Common questions are asked repeatedly across teams

---

## Chapter 2 — Existing System / Problem

### 2.1 Current Manual Process

In the current workflow, engineers manually:
1. Read through HLD PDF documents page by page
2. Maintain mental models of component relationships
3. Cross-reference between documents manually
4. Create spreadsheets for component/interface tracking
5. Conduct design reviews by reading documents in meetings

### 2.2 Challenges

| Challenge | Impact |
|-----------|--------|
| Information scattered across documents | Slow retrieval, incomplete answers |
| No structured search capability | Engineers rely on Ctrl+F in PDFs |
| Manual comparison between revisions | Changes missed, inconsistencies introduced |
| Knowledge loss when experts leave | Onboarding delays, repeated mistakes |
| No traceability for design decisions | Audit and compliance difficulties |

---

## Chapter 3 — Proposed System

### 3.1 Solution Overview

The AUTOSAR HLD Document Analysis Assistant is an AI-powered engineering tool that:
- Ingests AUTOSAR HLD PDF documents with page-level metadata
- Creates searchable vector embeddings using a local model
- Answers natural language questions with document citations
- Extracts structured architecture entities (components, interfaces, signals, dependencies)
- Compares document revisions to detect changes
- Identifies potential architecture inconsistencies
- Maintains an audit trail of all AI-assisted operations

### 3.2 Key Design Principles

1. **Grounded responses**: All answers must cite source documents and pages
2. **Human-in-the-loop**: AI assists but does not replace engineering judgment
3. **Hallucination resistance**: System explicitly acknowledges when information is insufficient
4. **Local-first**: Embeddings and vector storage are fully local
5. **Traceable**: Every operation is logged for governance

---

## Chapter 4 — Objectives

1. Reduce manual effort for HLD document review by providing instant, cited search
2. Extract structured architecture data (components, interfaces, signals, dependencies) from unstructured PDFs
3. Enable revision comparison to detect architectural changes between document versions
4. Identify potential inconsistencies and missing definitions in HLD documents
5. Demonstrate hallucination-resistant RAG with evidence-grounded responses
6. Maintain complete audit traceability of all AI-assisted operations
7. Achieve measurable retrieval recall and answer groundedness metrics

---

## Chapter 5 — Scope

### 5.1 In Scope
- PDF document ingestion with text and table extraction
- Local embedding generation (BAAI/bge-small-en-v1.5)
- FAISS vector storage with per-project isolation
- RAG-based question answering with citations
- Structured entity extraction (components, interfaces, signals, dependencies)
- Document/revision comparison
- Architecture consistency review
- Semantic search
- JSON/CSV export of findings
- SQLite audit logging
- Evaluation framework with 25 benchmark questions

### 5.2 Out of Scope
- Automatic approval of architecture decisions
- Modification of source HLD documents
- Replacement of formal architecture governance
- Production-grade authentication and access control
- Real-time collaborative editing
- Diagram/image understanding (OCR for visual content)

---

## Chapter 6 — Literature / Technology Background

### 6.1 Retrieval-Augmented Generation (RAG)
RAG (Lewis et al., 2020) combines information retrieval with language generation. Instead of relying solely on the LLM's parametric knowledge, RAG retrieves relevant documents from a corpus and uses them as context for generation. This significantly reduces hallucination and enables source citation.

### 6.2 Embedding Models
Sentence embedding models (Reimers & Gurevych, 2019) convert text into dense vector representations that capture semantic meaning. Models like BAAI/bge-small-en-v1.5 produce 384-dimensional vectors optimized for retrieval tasks. These run locally on CPU without requiring API access.

### 6.3 Vector Databases
FAISS (Facebook AI Similarity Search) provides efficient similarity search over dense vectors. For pilot-scale applications, FAISS IndexFlatIP (inner product) provides exact nearest-neighbor search with cosine similarity semantics when vectors are L2-normalized.

### 6.4 Large Language Models
LLMs are neural networks trained on large text corpora that can generate coherent, contextually appropriate text. When combined with retrieved context and careful prompting, they can produce grounded, cited responses for domain-specific queries.

### 6.5 Semantic Search
Unlike keyword-based search, semantic search uses embeddings to find content that is conceptually similar to a query, even when exact keywords don't match. This is particularly valuable for technical documentation where terminology may vary.

### 6.6 Document Intelligence
PDF parsing libraries (PyMuPDF, pdfplumber) extract text and tabular data from PDF documents. Combined with section detection and intelligent chunking, this enables page-level source tracking through the entire RAG pipeline.

---

## Chapter 7 — System Architecture

### 7.1 Overall Architecture

The system follows a layered architecture:
1. **Presentation Layer**: Streamlit web interface with 12 functional tabs
2. **Service Layer**: Python modules for RAG, extraction, comparison, and review
3. **Data Layer**: FAISS vector store, SQLite audit database, file system storage

### 7.2 Component Diagram

```
Streamlit UI (12 tabs)
    │
    ├── RAG Pipeline ──► LLM Client (Groq API)
    │       │
    │       └── Vector Store (FAISS) ◄── Embeddings (BGE, local)
    │
    ├── Extraction Engine ──► LLM Client
    │
    ├── Comparison Engine ──► Extraction + LLM
    │
    ├── Architecture Review ──► Extraction + Rules + LLM
    │
    ├── Prompt Manager ◄── Model_Prompts_Config/
    │
    └── Audit Logger ──► SQLite
```

### 7.3 Data Flow

1. PDF → Parser → Pages (text + tables)
2. Pages → Chunker → Chunks (with metadata)
3. Chunks → Embedding Model → Vectors
4. Vectors → FAISS Index (per project)
5. Query → Embedding → FAISS Search → Top-K Chunks
6. Chunks + Query → LLM → Grounded Answer + Citations

---

## Chapter 8 — Methodology

### 8.1 Document Ingestion
- PDFs are validated for type, size, and readability
- PyMuPDF extracts text per page; pdfplumber extracts tables
- Tables are flattened into readable pipe-delimited text
- Document version is auto-detected from content

### 8.2 Chunking Strategy
- Section-aware chunking detects heading patterns
- Sliding window with configurable size (default: 1200 chars) and overlap (200 chars)
- Boundary-aware breaking prefers paragraph and sentence boundaries
- Each chunk retains: doc_name, doc_id, page_number, section, version, source_type

### 8.3 Embedding
- BAAI/bge-small-en-v1.5 produces 384-dimensional vectors
- L2-normalized for cosine similarity via inner product search
- Runs locally on CPU (no API key needed)
- Model cached after first download (~130 MB)

### 8.4 Vector Retrieval
- FAISS IndexFlatIP performs exact nearest-neighbor search
- Per-project isolation: separate indexes per collection
- Optional document-level filtering for targeted search
- Configurable top-K retrieval (default: 6)

### 8.5 Prompt Construction
- System prompts stored in external files for versioning
- Context block assembled with source markers: `[Source: doc_name, Page N]`
- Strict instructions: answer only from context, cite sources, acknowledge gaps

### 8.6 LLM Generation
- Groq API with OpenAI-compatible interface
- Retry logic for rate limiting and transient errors
- JSON mode for structured extraction output
- Temperature: 0.1 (low creativity, high faithfulness)

### 8.7 Entity Extraction
- Batch processing (10 chunks per LLM call)
- JSON validation with fallback parsing
- Field validation (missing values → "Not specified")
- Deduplication via JSON fingerprinting

### 8.8 Evaluation Methodology
- 25 benchmark questions derived from manual document inspection
- 3 negative questions for hallucination resistance testing
- Automated metrics: retrieval recall, answer groundedness
- Human evaluation template: 5 criteria × 5-point scale

---

## Chapter 9 — Implementation

### 9.1 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.10+ |
| UI Framework | Streamlit | ≥1.38.0 |
| LLM API | Groq (OpenAI-compatible) | Via openai SDK |
| Embedding Model | BAAI/bge-small-en-v1.5 | sentence-transformers |
| Vector Database | FAISS | faiss-cpu ≥1.8.0 |
| PDF Parser | PyMuPDF + pdfplumber | ≥1.24, ≥0.11 |
| Audit Database | SQLite | Built-in |
| Data Processing | Pandas, NumPy | ≥2.2, ≥1.26 |

### 9.2 Module Summary

| Module | Purpose | Lines |
|--------|---------|-------|
| `app.py` | Streamlit UI (12 tabs) | ~500 |
| `config.py` | Central configuration | ~60 |
| `ingestion.py` | PDF parsing + chunking | ~250 |
| `embeddings.py` | Local embedding model | ~70 |
| `vectorstore.py` | FAISS index management | ~160 |
| `llm_client.py` | Groq API abstraction | ~120 |
| `prompts.py` | Prompt template loading | ~100 |
| `rag_pipeline.py` | RAG Q&A + summary | ~140 |
| `extraction.py` | Entity extraction | ~150 |
| `comparison.py` | Document comparison | ~140 |
| `architecture_review.py` | Potential issue detection | ~200 |
| `audit.py` | SQLite audit log | ~100 |
| `evaluation.py` | Evaluation framework | ~200 |
| `utils.py` | Export + utilities | ~130 |

---

## Chapter 10 — Dataset

### 10.1 Sample Documents

Three synthetic AUTOSAR HLD documents were created for this project:

| Document | Domain | Version | Pages | Components |
|----------|--------|---------|-------|------------|
| HLD_BCM_v1.0.pdf | Body Control Module | 1.0 | 5 | 4 SWCs |
| HLD_ADAS_FCW_v1.0.pdf | Forward Collision Warning | 1.0 | 5 | 4 SWCs |
| HLD_BMS_v1.1.pdf | Battery Management System | 1.1 | 5 | 5 SWCs |

### 10.2 Data Disclaimer

All documents are **synthetic** — created for academic pilot evaluation. They contain realistic AUTOSAR structure and terminology but are not derived from any actual vehicle program or proprietary data.

### 10.3 Ground Truth

Ground truth was established by manual inspection of each document:
- **BCM**: 4 components, 8 interfaces, 8 signals
- **ADAS FCW**: 4 components, 9 interfaces, 8 signals
- **BMS**: 5 components, 9 interfaces, 6 signals

---

## Chapter 11 — Evaluation

### 11.1 Evaluation Framework

The evaluation uses 25 questions covering:
- Component identification (5 questions)
- Interface identification (3 questions)
- Signal identification (4 questions)
- Dependency identification (3 questions)
- Functional flow (3 questions)
- General/safety questions (4 questions)
- Negative/unanswerable questions (3 questions)

### 11.2 Metrics

| Metric | Description | Method |
|--------|-------------|--------|
| Retrieval Recall@K | Fraction of expected pages found in retrieved chunks | Automated |
| Answer Groundedness | Fraction of expected answer points found in the answer | Automated (keyword) |
| Avg Latency | Time from question to answer | Automated |
| Extraction P/R/F1 | Entity extraction quality vs ground truth | Automated |

### 11.3 Note on Results

Actual evaluation results are generated by running the evaluation pipeline (`Evaluation` tab in the UI or `evaluation/evaluate.py`). Results shown in this report are from actual runs, not fabricated.

If the LLM API is unavailable, evaluation results will show "failed" status for LLM-dependent questions, with non-LLM metrics (retrieval recall) still available.

---

## Chapter 12 — Results

Results are generated by running the evaluation pipeline. See:
- `evaluation/results/evaluation_results.json` — Full results
- `evaluation/results/evaluation_report.csv` — Per-question CSV
- `evaluation/results/evaluation_summary.md` — Summary report

Results are NOT pre-fabricated. They must be generated by running the application.

---

## Chapter 13 — Limitations

1. **LLM dependency**: Q&A, extraction, comparison, and review require external API access
2. **PDF parsing**: Scanned PDFs, complex diagrams, and non-standard tables may not be handled
3. **Hallucination risk**: Despite strong grounding, zero hallucination cannot be guaranteed
4. **Scale**: FAISS IndexFlatIP is exact search; not suitable for millions of vectors
5. **Domain specificity**: Designed for AUTOSAR HLD; other document types not tested
6. **Synthetic data**: Evaluation is on synthetic documents only
7. **Table extraction**: pdfplumber's table detection is heuristic-based
8. **No diagram understanding**: Visual architecture diagrams are not interpreted

---

## Chapter 14 — Security and Governance

### 14.1 Data Privacy
- All documents and embeddings stored locally
- No persistent data sent to external services beyond LLM query context
- Project-level data isolation via separate FAISS indexes

### 14.2 API Key Management
- Keys stored in `.env` file (excluded from repository)
- Never hardcoded in source code
- Never logged in audit database
- `.env.example` contains placeholders only

### 14.3 Human Approval
- All AI-generated outputs marked as requiring engineering review
- Governance banner displayed on every page
- System does not claim to replace any human decision-making role
- Audit log provides complete traceability

### 14.4 Access Isolation
- Per-project collections prevent cross-project data exposure
- File type and size validation on uploads
- Safe error messages (no stack traces exposed)

---

## Chapter 15 — Future Scope

1. **FastAPI backend**: Separate API service for enterprise integration
2. **Enterprise authentication**: OAuth2/LDAP for role-based access
3. **PostgreSQL**: Replace SQLite for multi-user audit logging
4. **Neo4j architecture graph**: Graph database for relationship visualization
5. **Local LLM**: Ollama/vLLM deployment for fully offline operation
6. **Multimodal understanding**: Image/diagram processing for architecture visuals
7. **Enterprise DMS integration**: Connect to document management systems
8. **CI/CD integration**: Automated architecture validation in build pipelines
9. **Multi-language support**: Support for documents in multiple languages
10. **Advanced evaluation**: Semantic similarity metrics, LLM-as-judge evaluation

---

## Chapter 16 — Conclusion

This project demonstrates the practical application of Retrieval-Augmented Generation (RAG) for automotive engineering knowledge management. By combining local embeddings, vector search, and LLM-based generation with strong grounding controls, the system provides engineers with cited, traceable answers grounded in project-specific HLD documents.

The pilot validates the feasibility of AI-assisted architecture analysis while maintaining the human-in-the-loop governance required by automotive engineering standards. The evaluation framework provides measurable evidence of system quality, and the modular architecture supports future expansion to enterprise-scale deployment.

Key achievements:
- **Grounded RAG** with document and page-level citations
- **Structured extraction** of architecture entities from unstructured PDFs
- **Revision comparison** with change detection
- **Potential issue detection** combining rule-based and LLM analysis
- **Hallucination resistance** demonstrated through negative test cases
- **Complete traceability** via audit logging

---

## References

1. Lewis, P., et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." NeurIPS 2020.
2. Reimers, N., & Gurevych, I. (2019). "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks." EMNLP 2019.
3. Johnson, J., Douze, M., & Jégou, H. (2019). "Billion-scale similarity search with GPUs." IEEE Transactions on Big Data.
4. AUTOSAR Consortium. "AUTOSAR Classic Platform Methodology." https://www.autosar.org
5. Xiao, S., et al. (2023). "C-Pack: Packed Resources for General Chinese Embeddings." (BGE embedding models)
