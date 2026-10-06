# Demo Script — AUTOSAR HLD Document Analysis Assistant

## Demonstration Guide (5–10 minutes)

### Prerequisites
- Application running: `streamlit run app.py`
- Groq API key configured in `.env`
- Sample documents available in `sample_docs/`

---

### 0:00–0:45 — Problem Statement

**What to say:**
> "Automotive engineering teams work with large AUTOSAR High-Level Design documents — often hundreds of pages of components, interfaces, signals, and dependencies. Manual review is slow, error-prone, and difficult to trace. This project demonstrates an AI assistant that automates extraction, search, and validation of architectural knowledge from HLD documents."

**What to show:**
- The application title and governance banner
- The About tab briefly

---

### 0:45–1:30 — Architecture Overview

**What to say:**
> "The system uses Retrieval-Augmented Generation. Documents are parsed, chunked, and embedded using a local model. FAISS stores vectors for semantic search. When an engineer asks a question, relevant chunks are retrieved and fed to an LLM that generates grounded, cited answers."

**What to show:**
- Dashboard tab showing system configuration
- Point out: local embeddings, FAISS, Groq LLM

---

### 1:30–2:30 — Document Ingestion

**What to do:**
1. Go to the **Dashboard** tab
2. Click **"Ingest All Sample Documents"** button
3. Wait for all 3 documents to be processed
4. Show the updated statistics (documents, chunks, pages)

**What to say:**
> "Each PDF is parsed page by page — extracting text and tables. Content is chunked with overlap to preserve context, and each chunk retains its source document, page number, and section. This ensures we can cite sources accurately."

---

### 2:30–4:00 — RAG Question Answering

**What to do:**
1. Go to the **Ask AI** tab
2. Click sample question: **"What signals does SWC_DoorLockControl use?"**
3. Show the answer with inline citations
4. Expand the **Evidence** section — show source chunks with similarity scores
5. Ask a second question: **"What is the functional flow for contactor closing in the BMS?"**
6. Point out the grounding indicator

**What to say:**
> "The system retrieves the most relevant chunks, assembles them as context, and instructs the LLM to answer only from this evidence. Every claim has a citation. If information isn't available, the system says so rather than hallucinating."

**Negative test:**
7. Ask: **"What is the engine oil pressure sensor calibration value?"**
8. Show that the system correctly reports insufficient evidence

---

### 4:00–5:00 — Architecture Entity Extraction

**What to do:**
1. Go to the **Architecture** tab
2. Select `HLD_BCM_v1.0.pdf`
3. Click **"Run Extraction"**
4. Show the Components table (4 components)
5. Show the Interfaces table (8 ports)
6. Show the Signals table (8 signals)
7. Show the Dependencies table

**What to say:**
> "The system extracts structured architecture data — components, interfaces, signals, and dependencies — with source page numbers. This creates a searchable inventory from unstructured PDF content."

---

### 5:00–6:00 — Document Comparison

**What to do:**
1. Go to the **Compare** tab
2. Select Document A: any BCM document, Document B: BMS document
3. Or compare two BMS versions if both are available
4. Click **Compare Documents**
5. Show the change summary table
6. Show the entity count comparison
7. Expand the detailed report

**What to say:**
> "Engineers can compare document revisions to see what was added, removed, or changed. The system detects changes at the component, interface, signal, and dependency level."

---

### 6:00–7:00 — Architecture Review (Potential Issues)

**What to do:**
1. Go to the **Review Issues** tab
2. Select a document
3. Click **"Run Architecture Review"**
4. Show the severity summary metrics
5. Expand 1–2 issues showing evidence and recommendations

**What to say:**
> "The review combines rule-based checks with LLM analysis to detect potential issues — like undefined references or missing definitions. Every finding is labeled as a 'potential issue' requiring engineering verification."

---

### 7:00–8:00 — Evaluation

**What to do:**
1. Go to the **Evaluation** tab
2. Show the 25 evaluation questions (including 3 negative/hallucination tests)
3. If time permits, click **"Run Full Evaluation"**
4. Show metrics: retrieval recall, groundedness, latency
5. Show the human evaluation template

**What to say:**
> "We evaluate using 25 questions derived from actual document content, including negative tests for hallucination resistance. Metrics include retrieval recall and answer groundedness."

---

### 8:00–9:00 — Limitations and Governance

**What to say:**
> "This system does NOT replace architects or safety engineers. It does not approve designs or validate compliance. All AI-generated results are clearly marked as requiring engineering review. The LLM requires an external API — if unavailable, local features like search and ingestion still work. The system uses synthetic documents, not real production data."

**What to show:**
- The governance banner at the top of the page
- The About tab limitations section
- The audit log showing all actions are traced

---

### 9:00–10:00 — Conclusion

**What to say:**
> "This pilot demonstrates how RAG can ground LLM responses in project-specific documents, providing cited answers that engineers can verify. The system reduces manual review effort while maintaining traceability and governance. Future work includes local LLM deployment, enterprise authentication, and graph-based architecture visualization."

**What to show:**
- Export tab (download JSON/CSV)
- Audit log with full action history
- Final dashboard with all statistics

---

## Demo Questions (Ready to Use)

| # | Question | Expected Behavior |
|---|---------|-------------------|
| 1 | What signals does SWC_DoorLockControl use? | Lists DoorLockCmd, DoorStatus with citations to BCM Page 3-4 |
| 2 | What is the functional flow for contactor closing? | Describes 6-step sequence with BMS Page 4 citation |
| 3 | What are the main components of the BCM? | Lists 4 SWCs with ECU mapping |
| 4 | What interfaces are used by the ADAS FCW system? | Lists radar/camera ports with ADAS Page 3 citations |
| 5 | What changed between BMS v1.0 and v1.1? | Identifies CellBalancingController addition, SoHEstimate |
| 6 | What is the engine oil pressure sensor calibration value? | **Correctly reports: insufficient evidence** |
| 7 | What ASIL level is the FCW function? | ASIL B, with safety notes citation |
