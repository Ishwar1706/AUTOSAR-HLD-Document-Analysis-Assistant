# AUTOSAR HLD Document Analysis Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)
[![FAISS](https://img.shields.io/badge/VectorStore-FAISS-green.svg)](https://github.com/facebookresearch/faiss)
[![Tests](https://img.shields.io/badge/Tests-94%20passed-brightgreen.svg)]()
[![Case Study](https://img.shields.io/badge/Automotive-Case%20Study%201-orange.svg)]()

> **Applied AI/ML Academic & Engineering Project**  
> **Case Study 1: Automotive Engineering AI — AUTOSAR High-Level Design (HLD) Document Analysis Assistant**  
> An enterprise-grade, retrieval-augmented engineering assistant for ingesting, querying, extracting, comparing, and reviewing automotive architecture specifications grounded in AUTOSAR Classic High-Level Design documents.

---

## 📌 Executive Summary

Automotive High-Level Design (HLD) documents define Software Components (SWCs), ports, interfaces, signals, inter-component dependencies, and functional execution flows for Electronic Control Units (ECUs). In real-world automotive programs (e.g., Body Control Modules, ADAS Forward Collision Warning, Battery Management Systems), these documents span hundreds of pages across multiple revisions.

Engineering teams spend substantial engineering hours:
- Manually searching through revisions for interface modifications.
- Verifying cross-component signal compatibility and unmapped sender-receiver ports.
- Identifying missing timing constraints and ASIL safety classification gaps.
- Tracing functional flows and impact analysis for engineering change requests (ECRs).

The **AUTOSAR HLD Document Analysis Assistant** automates architectural knowledge extraction, semantic retrieval with page-level citations, cross-revision differential analysis, and automated architectural rule checking using a local embedding model (`BAAI/bge-small-en-v1.5`), FAISS vector indexing, and Groq-hosted open LLMs (`openai/gpt-oss-120b` or `openai/gpt-oss-20b`).

---

## 🏛️ System Architecture

```
   ┌────────────────────────────────────────────────────────────────────────┐
   │                          Streamlit User Interface                      │
   │  Dashboard | Documents | Ask AI | Architecture | Compare | Review ...  │
   └───────────────▲────────────────────────────────────────▲───────────────┘
                   │                                        │
┌──────────────────▼──────────────────┐   ┌─────────────────▼───────────────┐
│         Ingestion Pipeline          │   │      Retrieval & LLM Engine     │
│ ┌─────────────────────────────────┐ │   │ ┌─────────────────────────────┐ │
│ │  PyMuPDF & pdfplumber Parser    │ │   │ │ Dense Vector Search (FAISS) │ │
│ └────────────────┬────────────────┘ │   │ └──────────────┬──────────────┘ │
│                  ▼                  │   │                ▼                │
│ ┌─────────────────────────────────┐ │   │ ┌─────────────────────────────┐ │
│ │  Structure-Aware Chunker        │ │   │ │ Context Assembly & Prompt   │ │
│ └────────────────┬────────────────┘ │   │ └──────────────┬──────────────┘ │
│                  ▼                  │   │                ▼                │
│ ┌─────────────────────────────────┐ │   │ │ Groq LLM (gpt-oss-120b/20b)│ │
│ │  BGE-small-en-v1.5 Embeddings   │ │   │ └──────────────┬──────────────┘ │
│ └────────────────┬────────────────┘ │   │                ▼                │
│                  ▼                  │   │ ┌─────────────────────────────┐ │
│ ┌─────────────────────────────────┐ │   │ │ Grounded Answer + Citations │ │
│ │  FAISS Index + Project Metadata │ │   │ └─────────────────────────────┘ │
│ └─────────────────────────────────┘ │   └─────────────────────────────────┘
└─────────────────────────────────────┘
```

### Core Pipelines
1. **Document Ingestion & Preprocessing**:
   - Multi-page PDF text and structured table extraction via PyMuPDF and pdfplumber.
   - Section-aware sliding window chunking (default: 800 characters, 150 characters overlap) preserving document, version, and page metadata.
2. **Local Vector Storage**:
   - `BAAI/bge-small-en-v1.5` embeddings (384-dimensional, L2-normalized) executed locally on CPU/GPU without third-party API exposure.
   - Project-isolated FAISS `IndexFlatIP` stores cosine similarity indices persisted under `data/vector_store/<project_id>/`.
3. **Retrieval-Augmented Generation (RAG)**:
   - Top-$K$ semantic similarity retrieval with document filtering capability.
   - Automotive-specialized prompt templates with strict hallucination guards ("If the context does not contain sufficient information, state what is missing").
   - Explicit page-level evidence citation (`[Source: <Doc>, Page <N>]`).
4. **Structured Entity Extraction**:
   - Zero-shot JSON extraction for Software Components (SWCs), Ports/Interfaces (Sender-Receiver, Client-Server), Signals, and Dependencies.
   - Robust JSON sanitization, schema validation, and deduplication.
5. **Architectural Comparison**:
   - Automated diff engine computing additions, deletions, modifications, and unchanged elements across document revisions.
6. **Rule-Based & LLM Architecture Review**:
   - Automated checks for unmapped ports, dangling signals, missing ASIL levels, unspecified periodicity, and circular dependencies.
7. **Compliance & Audit Logging**:
   - Persistent SQLite audit ledger tracking all queries, latency, token metrics, model parameters, and timestamps.

---

## 📂 Repository Structure

```
autosar_hld_assistant/
├── app.py                          # Streamlit engineering dashboard (12 tabs)
├── config.py                       # Centralized configuration & environment loader
├── requirements.txt                # Python dependencies with pinned versions
├── run_evaluation.py               # CLI benchmark evaluation runner
├── .env.example                    # Template for API keys and runtime parameters
├── README.md                       # Complete project documentation and guide
│
├── src/                            # Core modular Python packages
│   ├── ingestion.py                # PDF extraction, table formatting, chunking
│   ├── embeddings.py               # Local BGE embedding model wrapper
│   ├── vectorstore.py              # FAISS vector store manager per project
│   ├── llm_client.py               # Groq LLM API client with retry & fallbacks
│   ├── rag_pipeline.py             # Cited Q&A and document summarization
│   ├── extraction.py               # Structured entity extraction and JSON validation
│   ├── comparison.py               # Architectural revision diff engine
│   ├── architecture_review.py      # Automotive architectural checks & issue scanner
│   ├── evaluation.py               # Recall, groundedness, F1 benchmark metrics
│   ├── audit.py                    # SQLite audit logging and metrics
│   ├── prompts.py                  # Automotive prompt loader and fallbacks
│   └── utils.py                    # Export helpers (JSON/CSV) & report generator
│
├── tests/                          # Automated test suite (94 tests)
│   ├── test_chunking.py            # Chunking, overlap, and section header tests
│   ├── test_comparison.py          # Differential comparison engine tests
│   ├── test_extraction.py          # JSON sanitization and entity validation tests
│   ├── test_ingestion.py           # PDF parsing, metadata, table formatting tests
│   ├── test_rag.py                 # Retrieval recall, groundedness, prompt tests
│   └── test_vectorstore.py         # FAISS CRUD, search, and persistence tests
│
├── sample_docs/                    # Synthetic AUTOSAR HLD test documents
│   ├── HLD_BCM_v1.0.pdf            # Body Control Module specification
│   ├── HLD_ADAS_FCW_v1.0.pdf       # Forward Collision Warning specification
│   └── HLD_BMS_v1.1.pdf            # Battery Management System specification
│
├── evaluation/                     # Benchmark dataset & ground truth
│   ├── questions.json              # 20 curated architectural evaluation questions
│   └── ground_truth.json           # Ground truth entities, source pages & rubric
│
├── Model_Prompts_Config/           # Prompt engineering templates & model configurations
│   ├── model_config.json           # Model parameters (temperature, max_tokens, etc.)
│   ├── rag_prompt_v1.txt           # RAG Q&A prompt with citation instructions
│   ├── extraction_prompt_v1.txt    # Entity extraction prompt with JSON schema
│   ├── comparison_prompt_v1.txt    # Differential analysis prompt
│   ├── review_prompt_v1.txt        # Architecture review and rule-checking prompt
│   └── summary_prompt_v1.txt       # Executive architecture summary prompt
│
├── Documentation/                  # Comprehensive academic & engineering documentation
│   ├── Technical_Report.md         # 16-chapter exhaustive academic technical report
│   ├── System_Architecture.md      # Detailed architectural diagrams & data flow specs
│   ├── Demo_Script.md              # 10-minute step-by-step presentation & demo script
│   └── Limitations.md              # Technical boundaries, assumptions & constraints
│
├── Synopsis/                       # Academic submission synopsis
│   └── Approved_Project_Synopsis.md# Formal academic project synopsis document
│
├── Declarations/                   # Submission compliance forms
│   ├── Student_Declaration.md      # Signed academic integrity declaration
│   └── Faculty_Approval_Placeholder.md # Academic supervisor review & sign-off form
│
├── Input_Data/                     # Ingested datasets & specification description
│   ├── HLD_BCM_v1.0.pdf
│   ├── HLD_ADAS_FCW_v1.0.pdf
│   ├── HLD_BMS_v1.1.pdf
│   └── dataset_description.md      # Comprehensive dataset and schema overview
│
└── Video/                          # Video presentation documentation
    └── Video_Readme.md             # Demonstration recording checklist and guide
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12 (Tested on Windows, Linux, macOS)
- Free Groq API Key ([Get one here](https://console.groq.com/keys))

### 2. Environment Setup

```bash
# Clone the repository and navigate to the project directory
cd "autosar_hld_assistant case study 1"

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (cmd):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. API Key Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and provide your Groq API key:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
CHUNK_SIZE_CHARS=800
CHUNK_OVERLAP_CHARS=150
TOP_K_RETRIEVAL=5
LLM_TEMPERATURE=0.1
MAX_TOKENS=2048
```

> **Note on Embedding Model**: On first run, `sentence-transformers` automatically downloads `BAAI/bge-small-en-v1.5` (~130 MB) to your local Hugging Face cache. Subsequent runs are fully cached and function completely offline.

### 4. Launching the Dashboard

```bash
streamlit run app.py
```

The application opens in your default browser at `http://localhost:8501`.

---

## 🖥️ Feature Walkthrough

The Streamlit dashboard features 12 dedicated engineering workspaces:

| Workspace Tab | Functionality |
|---|---|
| **0. Dashboard** | Real-time overview of indexed documents, total chunks, queries executed, configuration parameters, and a 1-click button to ingest sample documents. |
| **1. Documents** | Drag-and-drop PDF ingestion, page count analysis, chunk preview with metadata inspection, and document deletion. |
| **2. Ask AI** | Grounded Q&A with strict page citations, expandable retrieved evidence blocks, sample question selector, and similarity scores. |
| **3. Architecture** | Structured extraction of Software Components, Ports & Interfaces, Signals, and Inter-SWC Dependencies with tabular presentation. |
| **4. Summary** | Executive architectural summaries detailing document purpose, main SWCs, key signals, and safety assumptions. |
| **5. Compare** | Side-by-side revision diff (e.g., v1.0 vs v1.1) highlighting Added, Removed, Modified, and Unchanged elements. |
| **6. Review Issues** | Automated architectural rule verification flagging unmapped ports, dangling signals, missing ASIL tags, and periodicity gaps. |
| **7. Search** | Raw vector similarity inspection returning Top-$K$ semantic chunks with exact similarity scores and page references. |
| **8. Evaluation** | Automated benchmark runner displaying Retrieval Recall, Answer Groundedness, extraction F1, and latency metrics against ground truth. |
| **9. Exports** | Single-click exports of extracted entities, differential analyses, and issue reviews into JSON and CSV formats. |
| **10. Audit Log** | Traceable SQLite audit log recording every user action, timestamp, execution latency, and token consumption. |
| **11. About** | Case study background, AUTOSAR architectural concepts, methodology, and engineering governance notices. |

---

## 🧪 Automated Testing & Evaluation

### 1. Running the Automated Test Suite

The project includes 94 comprehensive unit and integration tests covering chunking, ingestion, vector store operations, RAG pipelines, entity extraction, and comparison logic.

Run the test suite via pytest:

```bash
python -m pytest tests/ -v
```

**Test Execution Results:**
```
============================= test session starts =============================
platform win32 -- Python 3.13.x, pytest-8.3.x
collected 94 items

tests/test_chunking.py::TestChunking::test_empty_input PASSED             [  1%]
...
tests/test_comparison.py::TestChangeSummary::test_added_component PASSED   [ 19%]
...
tests/test_extraction.py::TestSafeJsonParse::test_valid_json PASSED       [ 25%]
...
tests/test_ingestion.py::TestPDFIngestion::test_ingest_bcm PASSED          [ 59%]
...
tests/test_rag.py::TestAnswerGroundedness::test_all_points_found PASSED   [ 74%]
...
tests/test_vectorstore.py::TestVectorStoreBasic::test_persistence PASSED  [ 88%]
tests/test_vectorstore.py::TestVectorStoreCollections::test_delete_collection PASSED [100%]

======================== 94 passed, 1 warning in 6.2s =========================
```

### 2. Running the Benchmark Evaluation

Run the automated evaluation harness directly from the command line:

```bash
python run_evaluation.py --project demo_project --ingest-samples
```

Metrics computed:
- **Retrieval Recall**: Fraction of expected ground-truth document pages successfully retrieved in Top-$K$.
- **Answer Groundedness**: Key architectural facts and requirements accurately mentioned in the generated response.
- **Extraction F1**: Precision, Recall, and F1 score for extracted components, interfaces, and signals against the curated ground truth dataset.
- **Query Latency**: Wall-clock end-to-end execution time per query.

---

## 📑 Academic Documentation

Complete documentation is provided in the repository adhering to academic standards:

1. [Technical Report](file:///c:/Users/HP/Downloads/CS_1-main/CS_1-main/autosar_hld_assistant%20case%20study%201/Documentation/Technical_Report.md): 16 chapters covering Problem Formulation, AUTOSAR Concepts, Related Work, System Design, RAG Mechanics, Prompt Engineering, Evaluation Results, Failure Modes, and Future Roadmaps.
2. [System Architecture](file:///c:/Users/HP/Downloads/CS_1-main/CS_1-main/autosar_hld_assistant%20case%20study%201/Documentation/System_Architecture.md): Complete architectural diagrams, ASCII flow charts, data contracts, and component schemas.
3. [Demo Script](file:///c:/Users/HP/Downloads/CS_1-main/CS_1-main/autosar_hld_assistant%20case%20study%201/Documentation/Demo_Script.md): Step-by-step 10-minute presentation guide with exact test queries and expected answers.
4. [Limitations & Boundary Conditions](file:///c:/Users/HP/Downloads/CS_1-main/CS_1-main/autosar_hld_assistant%20case%20study%201/Documentation/Limitations.md): Analysis of token constraints, model dependencies, parsing trade-offs, and failure recovery.
5. [Project Synopsis](file:///c:/Users/HP/Downloads/CS_1-main/CS_1-main/autosar_hld_assistant%20case%20study%201/Synopsis/Approved_Project_Synopsis.md): Academic submission synopsis.
6. [Student Declaration](file:///c:/Users/HP/Downloads/CS_1-main/CS_1-main/autosar_hld_assistant%20case%20study%201/Declarations/Student_Declaration.md): Academic integrity and submission form.
7. [Faculty Approval Form](file:///c:/Users/HP/Downloads/CS_1-main/CS_1-main/autosar_hld_assistant%20case%20study%201/Declarations/Faculty_Approval_Placeholder.md): Review and sign-off template.

---

## ⚠️ Engineering Governance Disclaimer

> **IMPORTANT**: This software is an engineering assistance tool intended for architectural exploration and analysis. All extracted entities, comparative diffs, and generated answers are derived from statistical language models and MUST undergo formal review by qualified automotive systems and software safety engineers before being incorporated into production release baselines, safety cases (ISO 26262), or ASPICE work products.
