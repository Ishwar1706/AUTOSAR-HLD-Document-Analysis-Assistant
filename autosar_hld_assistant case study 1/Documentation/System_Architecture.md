# System Architecture — AUTOSAR HLD Document Analysis Assistant

## Overview

The AUTOSAR HLD Document Analysis Assistant is an AI-powered engineering tool that uses Retrieval-Augmented Generation (RAG) to help engineers analyze, search, compare, and validate architectural knowledge from AUTOSAR High-Level Design documents.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Web Interface                      │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │Dashboard │Documents │ Ask AI   │Architect.│ Compare  │ ...   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                    Application Services (Python)                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ RAG        │ │ Extraction │ │ Comparison │ │ Architecture │ │
│  │ Pipeline   │ │ Engine     │ │ Engine     │ │ Review       │ │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └──────┬───────┘ │
│        │              │              │               │          │
│  ┌─────┴──────────────┴──────────────┴───────────────┴───────┐  │
│  │              Prompt Management (prompts.py)                │  │
│  │              External prompt files (Model_Prompts_Config/) │  │
│  └────────────────────────┬──────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  LLM Client  │   │  Embeddings  │   │  Vector Store│
│  (Groq API)  │   │  (local BGE) │   │  (FAISS)     │
│  External    │   │  No API key  │   │  Local disk  │
└──────────────┘   └──────────────┘   └──────────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    │   SQLite Audit DB  │
                                    └───────────────────┘
```

## RAG Pipeline

```
User Question
      │
      ▼
Query Embedding (BAAI/bge-small-en-v1.5, local)
      │
      ▼
FAISS Vector Search (top-K similar chunks)
      │
      ▼
Context Assembly (with source citations)
      │
      ▼
LLM Generation (Groq API, grounded prompt)
      │
      ▼
Grounded Answer + Source Citations
      │
      ▼
Confidence/Grounding Indicator
      │
      ▼
Audit Log Entry
```

## Document Ingestion Pipeline

```
PDF Upload
      │
      ▼
File Validation (type, size, readability)
      │
      ▼
Text Extraction (PyMuPDF — per page)
      │
      ▼
Table Extraction (pdfplumber — per page)
      │
      ▼
Content Merging (text + tables per page)
      │
      ▼
Version Detection (auto-detect from text)
      │
      ▼
Section Detection (heading patterns)
      │
      ▼
Section-Aware Chunking (with overlap)
      │
      ▼
Metadata Attachment (doc_name, page, section, version, chunk_id)
      │
      ▼
Embedding (BAAI/bge-small-en-v1.5, local)
      │
      ▼
FAISS Index (per-project, persisted to disk)
```

## Entity Extraction Pipeline

```
Document Chunks (from FAISS)
      │
      ▼
Batch Processing (10 chunks per batch)
      │
      ▼
LLM Structured Extraction (JSON mode)
      │
      ▼
JSON Validation + Fallback Parsing
      │
      ▼
Entity Field Validation ("Not specified" for missing)
      │
      ▼
Deduplication (fingerprint-based)
      │
      ▼
Structured Output:
  - Components (name, responsibility, ECU, source)
  - Interfaces (port, direction, type, owner, source)
  - Signals (name, data type, range, description, source)
  - Dependencies (component, depends_on, type, source)
```

## Document Comparison Pipeline

```
Document A + Document B
      │              │
      ▼              ▼
Entity Extraction  Entity Extraction
      │              │
      ▼              ▼
Programmatic Diff (set-based name comparison)
      │
      ▼
LLM Qualitative Comparison
      │
      ▼
Structured Report:
  - Added / Removed / Modified / Unchanged
  - Potential inconsistencies
```

## Architecture Review Pipeline

```
Extracted Entities
      │
      ├──► Programmatic Checks (no LLM needed)
      │      - Orphan dependencies
      │      - Undefined references
      │      - Missing information
      │      - Components without interfaces
      │
      └──► LLM-Based Analysis (when API available)
             - Deeper inconsistency detection
             - Naming pattern analysis
             - Cross-reference validation
      │
      ▼
Combined Potential Issues List
  (issue_id, category, severity, evidence, recommendation)
```

## Data Storage

| Store | Technology | Location | Purpose |
|-------|-----------|----------|---------|
| Vector Index | FAISS | `data/vector_store/<project>/index.faiss` | Semantic search |
| Chunk Metadata | Pickle | `data/vector_store/<project>/chunks.pkl` | Source citations |
| Audit Log | SQLite | `data/audit_log.db` | Action traceability |
| Uploaded PDFs | Filesystem | `data/uploads/` | Document storage |

## Module Structure

```
app.py                  → Streamlit UI (12 tabs)
config.py               → Central configuration
src/
  ingestion.py          → PDF parsing + chunking
  embeddings.py         → Local embedding model
  vectorstore.py        → FAISS index management
  llm_client.py         → Groq API abstraction
  prompts.py            → Prompt template loading
  rag_pipeline.py       → RAG Q&A + summary
  extraction.py         → Entity extraction
  comparison.py         → Document comparison
  architecture_review.py → Potential issue detection
  audit.py              → SQLite audit log
  evaluation.py         → Evaluation framework
  utils.py              → Export + utilities
```

## Security Architecture

- API keys: Environment variables only (`.env`, excluded from repo)
- No hardcoded secrets in code
- Project-level data isolation (separate FAISS indexes)
- File validation on upload (type, size)
- No sensitive data in audit logs
- Safe error messages (no stack traces in production)
