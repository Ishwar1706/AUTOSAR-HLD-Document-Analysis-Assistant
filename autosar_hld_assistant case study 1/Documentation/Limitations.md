# Limitations — AUTOSAR HLD Document Analysis Assistant

## LLM Dependency
- The system requires an external LLM API (Groq) for question answering, entity extraction, comparison, review, and summary features.
- If the API is unavailable, document ingestion, semantic search, and embedding-based features continue to work.
- Responses depend on the LLM model's capability and may vary between model versions.

## PDF Parsing Limitations
- **Scanned PDFs**: Documents that are pure images (scanned without OCR) cannot have text extracted. The system will warn about this.
- **Complex diagrams**: Architecture diagrams, flowcharts, and visual elements in PDFs are not interpreted. Only text and table content is extracted.
- **Table extraction**: pdfplumber's table detection is heuristic-based. Complex, nested, or non-standard tables may not be extracted correctly.
- **Multi-column layouts**: Some multi-column PDF layouts may cause text to be extracted out of order.

## Hallucination Risk
- Despite strong grounding prompts, LLMs may occasionally generate information not present in the source documents.
- The system implements grounding indicators and citation requirements, but these are not guaranteed to catch all hallucinations.
- Negative test results show the system's hallucination resistance, but zero hallucination cannot be guaranteed.

## Entity Extraction Accuracy
- Extraction quality depends on:
  - Document structure and formatting
  - LLM model capability
  - Chunk boundaries (entities split across chunks may be missed or duplicated)
- Deduplication is fingerprint-based and may miss semantically identical entities with different wording.
- Extraction does not capture visual/diagram-based architecture relationships.

## Domain Coverage
- The system is designed for AUTOSAR HLD documents. Performance on other document types (safety manuals, test specifications) has not been evaluated.
- Architecture entity schemas are specific to AUTOSAR (SWC, ports, S/R interfaces) and may not generalize to other frameworks.

## Synthetic Dataset Limitations
- All sample documents are synthetic, created for pilot evaluation purposes.
- They are representative of real HLD structure but do not contain actual proprietary automotive data.
- Evaluation metrics are calculated on this synthetic dataset and may not reflect performance on real-world documents.

## Scale Limitations
- FAISS IndexFlatIP performs exhaustive search. For very large document collections (1000+ documents), approximate nearest neighbor methods would be needed.
- The system is designed for pilot-scale use (tens of documents, not thousands).
- Embedding model runs on CPU; large-scale embedding would benefit from GPU acceleration.

## Security Limitations
- No user authentication or role-based access control in the pilot.
- Project isolation is directory-based, not cryptographically enforced.
- API keys are managed via environment variables but the system does not implement key rotation or vault integration.

## Evaluation Limitations
- Automated metrics (retrieval recall, groundedness) use simple keyword/substring matching, not semantic similarity.
- Human evaluation template is provided but actual human ratings must be collected separately.
- The evaluation dataset (25 questions) is limited in scope and may not cover all edge cases.
