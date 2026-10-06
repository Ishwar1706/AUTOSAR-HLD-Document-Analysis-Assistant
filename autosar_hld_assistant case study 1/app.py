"""
AUTOSAR HLD Document Analysis Assistant — Main Application

Case Study 1 | Automotive Engineering AI
Streamlit-based engineering dashboard for HLD document analysis.

Run with:  streamlit run app.py
"""

import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

import config
from src.ingestion import ingest_pdf, validate_pdf, get_page_count
from src.vectorstore import VectorStore
from src.rag_pipeline import answer_question, summarize_document
from src.extraction import extract_entities, get_entity_counts
from src.comparison import compare_documents, format_comparison_table
from src.architecture_review import review_architecture
from src.audit import log_action, get_recent_logs, get_log_stats, get_action_types
from src.llm_client import (
    get_llm_info, LLMError, check_api_status,
    list_available_chat_models, normalize_model_name,
)
from src.embeddings import get_model_info
from src.utils import (
    export_entities_json, export_entities_csv, export_issues_csv,
    export_comparison_csv, generate_analysis_report, SAMPLE_QUESTIONS,
)
from src.evaluation import (
    load_evaluation_questions, load_ground_truth,
    run_rag_evaluation, save_evaluation_results,
    evaluate_extraction_precision_recall,
)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AUTOSAR HLD Analysis Assistant",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for professional appearance
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #a0c4ff; margin: 0.3rem 0 0 0; font-size: 0.95rem; }
    .governance-banner {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 0.8rem 1rem;
        border-radius: 0 6px 6px 0;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        color: #664d03;
    }
    .metric-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-card h3 { margin: 0; font-size: 1.5rem; color: #0f3460; }
    .metric-card p { margin: 0.2rem 0 0 0; font-size: 0.8rem; color: #6c757d; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>🔧 AUTOSAR HLD Document Analysis Assistant</h1>
    <p>Case Study 1 | Automotive Engineering AI</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="governance-banner">
    <strong>AI-assisted engineering analysis.</strong> Results are grounded in project documents
    but require engineering review before design, compliance, release, or validation decisions.
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar: Project settings
# ---------------------------------------------------------------------------
st.sidebar.title("Project Settings")

existing_collections = VectorStore.list_collections()
collection_mode = st.sidebar.radio(
    "Project workspace",
    ["Use existing", "Create new"],
    index=1 if not existing_collections else 0,
)

if collection_mode == "Create new" or not existing_collections:
    collection_name = st.sidebar.text_input("New project name", value="demo_project")
else:
    collection_name = st.sidebar.selectbox("Select project", existing_collections)

st.sidebar.markdown("---")
st.sidebar.markdown("**LLM Configuration**")

model_options = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
]
current_model = normalize_model_name(config.GROQ_MODEL)
if current_model not in model_options:
    model_options.insert(0, current_model)

selected_model = st.sidebar.selectbox(
    "Active Model",
    model_options,
    index=model_options.index(current_model) if current_model in model_options else 0,
)
config.GROQ_MODEL = selected_model
llm_info = get_llm_info()

if not config.GROQ_API_KEY:
    st.sidebar.warning("GROQ_API_KEY not set. Add it to .env")
else:
    st.sidebar.success("API key configured")

if st.sidebar.button("Test LLM Connection", key="btn_test_llm"):
    with st.sidebar.spinner("Connecting to Groq API..."):
        test_res = check_api_status(selected_model)
        if test_res.get("status") == "ok":
            st.sidebar.success(f"Connected to {selected_model}")
        else:
            st.sidebar.error(f"Error: {test_res.get('message')}")

st.sidebar.markdown("---")
st.sidebar.markdown("**Embedding Model**")
emb_info = get_model_info()
st.sidebar.text(f"{emb_info['model_name']}")
st.sidebar.text(f"Dim: {emb_info['embedding_dim']} | Local")

st.sidebar.markdown("---")
st.sidebar.markdown("**Chunking Settings**")
st.sidebar.text(f"Chunk size: {config.CHUNK_SIZE_CHARS} chars")
st.sidebar.text(f"Overlap: {config.CHUNK_OVERLAP_CHARS} chars")
st.sidebar.text(f"Top-K: {config.TOP_K_RETRIEVAL}")

if collection_name:
    store_preview = VectorStore(collection_name)
    stats = store_preview.stats()
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Project Stats**")
    st.sidebar.text(f"Documents: {stats['total_documents']}")
    st.sidebar.text(f"Chunks: {stats['total_chunks']}")

# ---------------------------------------------------------------------------
# Tab Navigation
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "Dashboard",
    "Documents",
    "Ask AI",
    "Architecture",
    "Summary",
    "Compare",
    "Review Issues",
    "Search",
    "Evaluation",
    "Exports",
    "Audit Log",
    "About",
])

# ---------------------------------------------------------------------------
# TAB 0: Dashboard
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Project Dashboard")

    store = VectorStore(collection_name)
    stats = store.stats()
    log_stats = get_log_stats(collection_name)

    # Metrics row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Documents", stats["total_documents"])
    c2.metric("Chunks Indexed", stats["total_chunks"])
    c3.metric("Total Queries", log_stats.get("by_action", {}).get("question_answering", 0))
    c4.metric("Extractions", log_stats.get("by_action", {}).get("entity_extraction", 0))
    c5.metric("Comparisons", log_stats.get("by_action", {}).get("document_comparison", 0))

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**System Configuration**")
        config_data = {
            "Setting": ["LLM Provider", "LLM Model", "Embedding Model", "Vector Database",
                        "Chunk Size", "Overlap", "Top-K Retrieval", "Temperature"],
            "Value": [llm_info["provider"], llm_info["model"], emb_info["model_name"],
                      "FAISS (local)", f"{config.CHUNK_SIZE_CHARS} chars",
                      f"{config.CHUNK_OVERLAP_CHARS} chars", str(config.TOP_K_RETRIEVAL),
                      str(config.LLM_TEMPERATURE)],
        }
        st.dataframe(pd.DataFrame(config_data), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**Indexed Documents**")
        if stats["documents"]:
            for doc_name in stats["documents"]:
                details = stats["document_details"].get(doc_name, {})
                st.markdown(
                    f"- **{doc_name}** — {details.get('chunks', 0)} chunks, "
                    f"{details.get('pages', '?')} pages, v{details.get('version', '?')}"
                )
        else:
            st.info("No documents ingested yet. Go to the Documents tab to upload.")

    # Sample documents quick-load
    st.markdown("---")
    st.markdown("**Quick Start — Load Sample Documents**")
    sample_dir = config.SAMPLE_DOCS_DIR
    sample_files = sorted(sample_dir.glob("*.pdf")) if sample_dir.exists() else []

    if sample_files:
        already_ingested = set(stats["documents"])
        new_samples = [f for f in sample_files if f.name not in already_ingested]

        if new_samples:
            st.write(f"Found {len(new_samples)} sample document(s) ready to ingest:")
            for f in new_samples:
                st.write(f"  - `{f.name}`")
            if st.button("Ingest All Sample Documents", type="primary"):
                store = VectorStore(collection_name)
                for pdf_path in new_samples:
                    with st.spinner(f"Processing {pdf_path.name}..."):
                        chunks = ingest_pdf(
                            str(pdf_path), pdf_path.name,
                            config.CHUNK_SIZE_CHARS, config.CHUNK_OVERLAP_CHARS,
                            project_id=collection_name,
                        )
                        store.add_chunks(chunks)
                        log_action(collection_name, "document_ingestion",
                                   f"Ingested {pdf_path.name} ({len(chunks)} chunks)",
                                   config.GROQ_MODEL, document=pdf_path.name)
                    st.success(f"{pdf_path.name} — {len(chunks)} chunks")
                st.rerun()
        else:
            st.success("All sample documents are already ingested.")
    else:
        st.info("No sample documents found in `sample_docs/` directory.")

# ---------------------------------------------------------------------------
# TAB 1: Documents
# ---------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Document Management")

    # Upload section
    st.markdown("#### Upload Documents")
    uploaded_files = st.file_uploader(
        "Choose PDF file(s)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload AUTOSAR HLD documents in PDF format.",
    )

    doc_version = st.text_input(
        "Document version (optional — auto-detected if blank)",
        placeholder="e.g. 1.0",
    )

    if st.button("Ingest Uploaded Document(s)", type="primary", disabled=not uploaded_files):
        store = VectorStore(collection_name)
        for uploaded_file in uploaded_files:
            # File size check
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size > config.MAX_UPLOAD_SIZE_MB:
                st.error(f"{uploaded_file.name}: File too large ({file_size:.1f} MB)")
                continue

            with st.spinner(f"Processing {uploaded_file.name}..."):
                save_path = config.UPLOAD_DIR / uploaded_file.name
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                try:
                    chunks = ingest_pdf(
                        str(save_path),
                        doc_name=uploaded_file.name,
                        chunk_size=config.CHUNK_SIZE_CHARS,
                        overlap=config.CHUNK_OVERLAP_CHARS,
                        project_id=collection_name,
                        document_version=doc_version if doc_version else None,
                    )
                    store.add_chunks(chunks)
                    log_action(
                        collection_name, "document_ingestion",
                        f"Ingested {uploaded_file.name} ({len(chunks)} chunks)",
                        config.GROQ_MODEL, document=uploaded_file.name,
                    )
                    st.success(f"{uploaded_file.name} — {len(chunks)} chunks indexed")
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {e}")
        st.rerun()

    # Document list
    st.markdown("---")
    st.markdown("#### Indexed Documents")
    store = VectorStore(collection_name)
    docs = store.document_names()
    if docs:
        for d in docs:
            doc_chunks = store.chunks_for_document(d)
            pages = sorted({c.page_number for c in doc_chunks})
            version = doc_chunks[0].document_version if doc_chunks else "?"
            with st.expander(f"**{d}** — v{version} | {len(doc_chunks)} chunks | {len(pages)} pages"):
                st.write(f"**Document Version:** {version}")
                st.write(f"**Pages:** {min(pages)}-{max(pages)}")
                st.write(f"**Total Chunks:** {len(doc_chunks)}")
                st.write(f"**Sections:** {', '.join(sorted({c.section for c in doc_chunks}))}")

                if st.button(f"Remove {d}", key=f"remove_{d}"):
                    store.remove_document(d)
                    st.success(f"Removed {d}")
                    st.rerun()
    else:
        st.info("No documents ingested yet. Upload PDFs above or use Quick Start on the Dashboard.")

# ---------------------------------------------------------------------------
# TAB 2: Ask AI (RAG Q&A)
# ---------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Ask a Question About Your Documents")

    store = VectorStore(collection_name)
    if store.is_empty():
        st.info("Ingest a document first in the Documents tab.")
    else:
        # Sample questions
        st.markdown("**Try a sample question:**")
        sample_cols = st.columns(2)
        selected_sample = None
        for i, q in enumerate(SAMPLE_QUESTIONS[:6]):
            col = sample_cols[i % 2]
            if col.button(q, key=f"sample_{i}", use_container_width=True):
                selected_sample = q

        question = st.text_input(
            "Your question",
            value=selected_sample or "",
            placeholder="e.g. What signals does SWC_DoorLockControl use?",
        )

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            top_k = st.number_input("Chunks to retrieve", min_value=1, max_value=20,
                                     value=config.TOP_K_RETRIEVAL)
        with col2:
            doc_filter = st.selectbox(
                "Filter by document",
                ["All documents"] + store.document_names(),
            )
        with col3:
            st.write("")  # spacer

        if st.button("Get Answer", type="primary", disabled=not question):
            filter_doc = None if doc_filter == "All documents" else doc_filter
            with st.spinner("Retrieving relevant sections and generating answer..."):
                try:
                    result = answer_question(
                        collection_name, question,
                        top_k=int(top_k), doc_filter=filter_doc,
                    )
                    latency_ms = int(result.latency_seconds * 1000)
                    log_action(
                        collection_name, "question_answering", question,
                        config.GROQ_MODEL, latency_ms=latency_ms,
                    )
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

            if result:
                # Grounding indicator
                if result.grounded:
                    st.success(f"Answer grounded in {result.num_chunks_retrieved} source chunks | {result.latency_seconds:.2f}s")
                else:
                    st.warning("Low confidence — limited evidence found in indexed documents")

                st.markdown("### Answer")
                st.write(result.answer)

                st.markdown("### Evidence")
                with st.expander(f"Source chunks ({len(result.sources)} retrieved)", expanded=True):
                    for i, c in enumerate(result.sources):
                        score = result.scores[i] if i < len(result.scores) else None
                        score_text = f" | Similarity: {score:.3f}" if score else ""
                        st.markdown(f"**{c.citation}**{score_text}")
                        st.text(c.text[:600] + ("..." if len(c.text) > 600 else ""))
                        st.markdown("---")

        # Document summary section
        st.markdown("---")
        st.subheader("Generate Document Summary")
        docs_for_summary = store.document_names()
        if docs_for_summary:
            doc_for_summary = st.selectbox("Select a document", docs_for_summary)
            if st.button("Generate Summary"):
                with st.spinner("Generating summary..."):
                    try:
                        result = summarize_document(collection_name, doc_for_summary)
                        log_action(collection_name, "document_summary",
                                   doc_for_summary, config.GROQ_MODEL,
                                   document=doc_for_summary)
                    except Exception as e:
                        st.error(f"Error: {e}")
                        result = None
                if result:
                    st.markdown("### Summary")
                    st.write(result.answer)

# ---------------------------------------------------------------------------
# TAB 3: Architecture Entity Extraction
# ---------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Architecture Entity Extraction")
    st.caption("Extract structured components, interfaces, signals, and dependencies from HLD documents.")

    store = VectorStore(collection_name)
    if store.is_empty():
        st.info("Ingest a document first.")
    else:
        doc_for_extraction = st.selectbox(
            "Select a document to extract from",
            store.document_names(), key="extract_doc",
        )

        if st.button("Run Extraction", type="primary"):
            with st.spinner("Extracting architecture entities..."):
                try:
                    result = extract_entities(collection_name, doc_for_extraction)
                    log_action(collection_name, "entity_extraction",
                               doc_for_extraction, config.GROQ_MODEL,
                               document=doc_for_extraction)
                    st.session_state["last_extraction"] = result
                    st.session_state["last_extraction_doc"] = doc_for_extraction
                except Exception as e:
                    st.error(f"Error: {e}")

        result = st.session_state.get("last_extraction")
        if result and st.session_state.get("last_extraction_doc") == doc_for_extraction:
            # Show counts
            counts = get_entity_counts(result)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Components", counts["components"])
            c2.metric("Interfaces", counts["interfaces"])
            c3.metric("Signals", counts["signals"])
            c4.metric("Dependencies", counts["dependencies"])

            # Tabs for entity categories
            entity_tabs = st.tabs(["Components", "Interfaces", "Signals", "Dependencies"])

            with entity_tabs[0]:
                items = result.get("components", [])
                if items:
                    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
                else:
                    st.info("No components extracted.")

            with entity_tabs[1]:
                items = result.get("interfaces", [])
                if items:
                    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
                else:
                    st.info("No interfaces extracted.")

            with entity_tabs[2]:
                items = result.get("signals", [])
                if items:
                    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
                else:
                    st.info("No signals extracted.")

            with entity_tabs[3]:
                items = result.get("dependencies", [])
                if items:
                    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
                else:
                    st.info("No dependencies extracted.")

            # Parse error warning
            meta = result.get("_metadata", {})
            if meta.get("parse_errors", 0) > 0:
                st.warning(f"Note: {meta['parse_errors']} batch(es) had JSON parse issues. Some entities may be missing.")

# ---------------------------------------------------------------------------
# TAB 4: Document Summary
# ---------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Document Summary")
    st.caption("Generate a structured HLD summary covering all key architecture aspects.")

    store = VectorStore(collection_name)
    if store.is_empty():
        st.info("Ingest a document first.")
    else:
        doc_for_summary = st.selectbox("Select document", store.document_names(), key="summary_doc")
        if st.button("Generate HLD Summary", type="primary", key="gen_summary"):
            with st.spinner("Generating comprehensive summary..."):
                try:
                    result = summarize_document(collection_name, doc_for_summary)
                    log_action(collection_name, "document_summary",
                               doc_for_summary, config.GROQ_MODEL,
                               document=doc_for_summary)
                    st.session_state["last_summary"] = result
                    st.session_state["last_summary_doc"] = doc_for_summary
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.session_state.get("last_summary") and st.session_state.get("last_summary_doc") == doc_for_summary:
            result = st.session_state["last_summary"]
            st.success(f"Summary generated in {result.latency_seconds:.2f}s using {result.num_chunks_retrieved} chunks")
            st.markdown(result.answer)

# ---------------------------------------------------------------------------
# TAB 5: Compare Documents
# ---------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Document / Revision Comparison")
    st.caption("Compare two HLD documents or revisions to detect changes.")

    store = VectorStore(collection_name)
    docs = store.document_names()
    if len(docs) < 2:
        st.info("Ingest at least two documents to enable comparison.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            doc_a = st.selectbox("Document A (baseline)", docs, key="doc_a")
        with col2:
            doc_b = st.selectbox("Document B (comparison)", docs, key="doc_b",
                                  index=min(1, len(docs) - 1))

        if st.button("Compare Documents", type="primary", disabled=(doc_a == doc_b)):
            with st.spinner("Extracting entities and comparing..."):
                try:
                    report = compare_documents(collection_name, doc_a, doc_b)
                    log_action(collection_name, "document_comparison",
                               f"{doc_a} vs {doc_b}", config.GROQ_MODEL)
                    st.session_state["last_comparison"] = report
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.session_state.get("last_comparison"):
            report = st.session_state["last_comparison"]

            # Change summary table
            st.markdown("### Change Summary")
            change_rows = format_comparison_table(report.get("change_summary", {}))
            if change_rows:
                st.dataframe(pd.DataFrame(change_rows), use_container_width=True, hide_index=True)

            # Entity counts comparison
            st.markdown("### Entity Counts")
            counts_a = report.get("entities_a_counts", {})
            counts_b = report.get("entities_b_counts", {})
            count_df = pd.DataFrame({
                "Category": list(counts_a.keys()),
                f"{report.get('doc_a', 'Doc A')}": list(counts_a.values()),
                f"{report.get('doc_b', 'Doc B')}": list(counts_b.values()),
            })
            st.dataframe(count_df, use_container_width=True, hide_index=True)

            # Detailed LLM report
            with st.expander("Detailed Comparison Report", expanded=True):
                st.markdown(report.get("report", "No report generated."))

# ---------------------------------------------------------------------------
# TAB 6: Review Issues
# ---------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Architecture Review — Potential Issues")
    st.caption("AI-assisted review checking for potential inconsistencies and missing information.")

    store = VectorStore(collection_name)
    if store.is_empty():
        st.info("Ingest a document first.")
    else:
        doc_for_review = st.selectbox("Select document to review",
                                       store.document_names(), key="review_doc")

        use_llm_review = st.checkbox("Include LLM-based analysis", value=True,
                                      help="Programmatic checks run regardless. LLM adds deeper analysis but requires API access.")

        if st.button("Run Architecture Review", type="primary"):
            # Use existing extraction if available
            existing_entities = None
            if (st.session_state.get("last_extraction") and
                    st.session_state.get("last_extraction_doc") == doc_for_review):
                existing_entities = st.session_state["last_extraction"]

            with st.spinner("Running architecture review..."):
                try:
                    review = review_architecture(
                        collection_name, doc_for_review,
                        entities=existing_entities,
                        use_llm=use_llm_review,
                    )
                    log_action(collection_name, "architecture_review",
                               doc_for_review, config.GROQ_MODEL,
                               document=doc_for_review)
                    st.session_state["last_review"] = review
                    st.session_state["last_review_doc"] = doc_for_review
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.session_state.get("last_review") and st.session_state.get("last_review_doc") == doc_for_review:
            review = st.session_state["last_review"]
            summary = review.get("summary", {})

            # Summary metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Issues", summary.get("total_issues", 0))
            c2.metric("High Severity", summary.get("high_severity", 0))
            c3.metric("Medium Severity", summary.get("medium_severity", 0))
            c4.metric("Low Severity", summary.get("low_severity", 0))

            if not review.get("llm_available") and use_llm_review:
                st.warning(f"LLM analysis unavailable: {review.get('llm_error', 'Unknown error')}. Showing programmatic checks only.")

            # Issues list
            issues = review.get("potential_issues", [])
            if issues:
                for issue in issues:
                    severity = issue.get("severity", "low")
                    icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(severity, "⚪")

                    with st.expander(f"{icon} [{issue.get('issue_id', '?')}] {issue.get('description', 'No description')[:100]}"):
                        st.write(f"**Category:** {issue.get('category', 'N/A')}")
                        st.write(f"**Severity:** {severity.title()}")
                        st.write(f"**Evidence:** {issue.get('evidence', 'N/A')}")
                        st.write(f"**Source:** {issue.get('source_document', 'N/A')}, Page {issue.get('source_page', 'N/A')}")
                        st.write(f"**Recommendation:** {issue.get('recommendation', 'N/A')}")
            else:
                st.success("No potential issues detected.")

# ---------------------------------------------------------------------------
# TAB 7: Search
# ---------------------------------------------------------------------------
with tabs[7]:
    st.subheader("Semantic Search")
    st.caption("Search across all indexed documents for architecture concepts, components, signals, and more.")

    store = VectorStore(collection_name)
    if store.is_empty():
        st.info("Ingest a document first.")
    else:
        search_query = st.text_input("Search query", placeholder="e.g. contactor control, door lock, sensor fusion")

        col1, col2 = st.columns(2)
        with col1:
            search_top_k = st.slider("Number of results", 1, 20, 10)
        with col2:
            search_doc_filter = st.selectbox(
                "Filter by document",
                ["All documents"] + store.document_names(),
                key="search_filter",
            )

        if st.button("Search", type="primary", disabled=not search_query):
            doc_filter = None if search_doc_filter == "All documents" else search_doc_filter
            results = store.search(search_query, top_k=search_top_k, doc_filter=doc_filter)

            if results:
                st.write(f"**{len(results)} results found:**")
                for i, (chunk, score) in enumerate(results):
                    with st.expander(
                        f"**{i+1}.** {chunk.citation} | Section: {chunk.section} | Score: {score:.3f}",
                        expanded=(i < 3),
                    ):
                        st.text(chunk.text)
                        st.caption(f"Chunk #{chunk.chunk_index} | Source type: {chunk.source_type} | Version: {chunk.document_version}")
            else:
                st.info("No results found for this query.")

# ---------------------------------------------------------------------------
# TAB 8: Evaluation
# ---------------------------------------------------------------------------
with tabs[8]:
    st.subheader("Evaluation Dashboard")
    st.caption("Run and view evaluation metrics for RAG quality assessment.")

    eval_tabs = st.tabs(["Run Evaluation", "View Results", "Ground Truth", "Human Evaluation"])

    with eval_tabs[0]:
        st.markdown("#### Run RAG Evaluation")
        questions = load_evaluation_questions()

        if not questions:
            st.warning("No evaluation questions found. Check `evaluation/questions.json`.")
        else:
            st.write(f"**{len(questions)} evaluation questions loaded.**")
            st.write("Question types: " + ", ".join(sorted({q.get("type", "?") for q in questions})))

            store = VectorStore(collection_name)
            if store.is_empty():
                st.warning("Ingest documents before running evaluation.")
            elif st.button("Run Full Evaluation", type="primary"):
                with st.spinner(f"Evaluating {len(questions)} questions..."):
                    try:
                        eval_results = run_rag_evaluation(collection_name, questions)
                        saved = save_evaluation_results(eval_results)
                        st.session_state["eval_results"] = eval_results
                        log_action(collection_name, "evaluation",
                                   f"Ran evaluation with {len(questions)} questions",
                                   config.GROQ_MODEL)
                        st.success(f"Evaluation complete. Results saved.")
                    except Exception as e:
                        st.error(f"Evaluation error: {e}")

    with eval_tabs[1]:
        st.markdown("#### Evaluation Results")

        eval_results = st.session_state.get("eval_results")

        # Try loading from file if not in session
        if not eval_results:
            results_path = config.BASE_DIR / "evaluation" / "results" / "evaluation_results.json"
            if results_path.exists():
                try:
                    with open(results_path) as f:
                        eval_results = json.load(f)
                except Exception:
                    pass

        if eval_results:
            summary = eval_results.get("summary", {})

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questions", summary.get("total_questions", 0))
            c2.metric("Avg Retrieval Recall", f"{summary.get('avg_retrieval_recall', 0):.2%}")
            c3.metric("Avg Groundedness", f"{summary.get('avg_groundedness', 0):.2%}")
            c4.metric("Avg Latency", f"{summary.get('avg_latency_seconds', 0):.2f}s")

            st.markdown("---")

            # Per-question results
            results = eval_results.get("results", [])
            if results:
                df = pd.DataFrame([{
                    "ID": r.get("id"),
                    "Type": r.get("type"),
                    "Retrieval Recall": r.get("retrieval_recall", "N/A"),
                    "Groundedness": r.get("groundedness_score", "N/A"),
                    "Sources": r.get("num_sources", 0),
                    "Latency (s)": r.get("latency_seconds", "N/A"),
                    "Status": r.get("status"),
                } for r in results])
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Show failed cases
                failed = [r for r in results if r.get("status") == "error"]
                if failed:
                    st.warning(f"{len(failed)} question(s) failed during evaluation.")
        else:
            st.info("No evaluation results available. Run the evaluation first.")

    with eval_tabs[2]:
        st.markdown("#### Ground Truth Data")
        gt = load_ground_truth()
        if gt:
            st.json(gt.get("extraction_ground_truth", {}))
        else:
            st.info("No ground truth file found.")

    with eval_tabs[3]:
        st.markdown("#### Human Evaluation Template")
        gt = load_ground_truth()
        template = gt.get("human_evaluation_template", {})
        if template:
            st.markdown("**Criteria:**")
            for criterion in template.get("criteria", []):
                st.write(f"- **{criterion['name']}** ({criterion['scale']}): {criterion['description']}")
            st.markdown(f"\n**Instructions:** {template.get('instructions', 'N/A')}")
            st.info("Human evaluation ratings should be recorded separately and are NOT auto-generated.")
        else:
            st.info("No human evaluation template found.")

# ---------------------------------------------------------------------------
# TAB 9: Exports
# ---------------------------------------------------------------------------
with tabs[9]:
    st.subheader("Export Data")

    # Extraction export
    result = st.session_state.get("last_extraction")
    if result:
        st.markdown("#### Extracted Entities")
        doc_name = st.session_state.get("last_extraction_doc", "extraction")

        col1, col2 = st.columns(2)
        with col1:
            json_str = export_entities_json(result, doc_name)
            st.download_button(
                "Download Entities (JSON)",
                data=json_str,
                file_name=f"{doc_name}_entities.json",
                mime="application/json",
            )

        with col2:
            for category in ("components", "interfaces", "signals", "dependencies"):
                items = result.get(category, [])
                if items:
                    csv_str = export_entities_csv(items, category)
                    st.download_button(
                        f"Download {category.title()} (CSV)",
                        data=csv_str,
                        file_name=f"{category}.csv",
                        mime="text/csv",
                        key=f"csv_{category}",
                    )
    else:
        st.info("Run an entity extraction first (Architecture tab) to enable entity exports.")

    st.markdown("---")

    # Comparison export
    comparison = st.session_state.get("last_comparison")
    if comparison:
        st.markdown("#### Comparison Results")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Comparison (JSON)",
                data=json.dumps(comparison, indent=2, default=str),
                file_name="comparison_report.json",
                mime="application/json",
            )
        with col2:
            csv_str = export_comparison_csv(comparison)
            if csv_str:
                st.download_button(
                    "Download Changes (CSV)",
                    data=csv_str,
                    file_name="comparison_changes.csv",
                    mime="text/csv",
                )

    # Review export
    review = st.session_state.get("last_review")
    if review:
        st.markdown("#### Review Issues")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Issues (JSON)",
                data=json.dumps(review, indent=2, default=str),
                file_name="review_issues.json",
                mime="application/json",
            )
        with col2:
            csv_str = export_issues_csv(review)
            if csv_str:
                st.download_button(
                    "Download Issues (CSV)",
                    data=csv_str,
                    file_name="potential_issues.csv",
                    mime="text/csv",
                )

    # Analysis report
    st.markdown("---")
    st.markdown("#### Generate Analysis Report")
    store = VectorStore(collection_name)
    stats = store.stats()
    if st.button("Generate Report"):
        extractions = {}
        if st.session_state.get("last_extraction"):
            doc = st.session_state.get("last_extraction_doc", "unknown")
            extractions[doc] = st.session_state["last_extraction"]

        reviews = {}
        if st.session_state.get("last_review"):
            doc = st.session_state.get("last_review_doc", "unknown")
            reviews[doc] = st.session_state["last_review"]

        report = generate_analysis_report(collection_name, stats, extractions, reviews)
        st.download_button(
            "Download Analysis Report",
            data=report,
            file_name="analysis_report.txt",
            mime="text/plain",
        )
        log_action(collection_name, "export", "Generated analysis report", config.GROQ_MODEL)

# ---------------------------------------------------------------------------
# TAB 10: Audit Log
# ---------------------------------------------------------------------------
with tabs[10]:
    st.subheader("Audit Log")
    st.caption("Record of all AI-assisted operations for traceability and governance.")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        action_types = get_action_types()
        filter_action = st.selectbox(
            "Filter by action",
            ["All"] + action_types,
        )
    with col2:
        filter_limit = st.number_input("Max entries", value=100, min_value=10, max_value=1000)

    action_filter = None if filter_action == "All" else filter_action
    logs = get_recent_logs(collection=collection_name, action_type=action_filter, limit=filter_limit)

    if logs:
        df = pd.DataFrame(
            logs,
            columns=["Timestamp (UTC)", "Project", "Action", "Details", "Document", "Model", "Status"],
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(logs)} entries.")
    else:
        st.info("No actions logged yet for this project.")

# ---------------------------------------------------------------------------
# TAB 11: About
# ---------------------------------------------------------------------------
with tabs[11]:
    st.subheader("About This System")

    st.markdown(f"""
    ### {config.PROJECT_TITLE}
    **{config.PROJECT_SUBTITLE}** | Version {config.VERSION}

    ---

    #### Purpose
    This system automates the extraction, organization, search, comparison, and validation
    assistance of architectural knowledge from AUTOSAR High-Level Design documents.
    It helps engineers work with HLD documents covering software components, interfaces,
    signals, dependencies, functional flows, and architecture relationships.

    #### What This System Does NOT Do
    - Replace architects, safety engineers, or cybersecurity engineers
    - Provide formal architecture governance or approval
    - Make compliance validation or production release decisions
    - Guarantee completeness or correctness of AI-generated analysis

    **All AI-generated results require human engineering review.**

    ---

    #### Technology Stack

    | Layer | Technology |
    |---|---|
    | UI | Streamlit |
    | LLM | {llm_info['provider']} — {llm_info['model']} |
    | Embeddings | {emb_info['model_name']} (local) |
    | Vector Store | FAISS (local, per-project) |
    | PDF Parsing | PyMuPDF + pdfplumber |
    | Audit Log | SQLite |
    | Language | Python |

    #### API Dependency
    - **Local (no internet after setup):** PDF processing, embeddings, FAISS, SQLite, application logic
    - **External API required:** LLM inference via Groq API

    If the Groq API is unavailable, document ingestion, search, and embeddings continue to work.
    Only LLM-dependent features (Q&A, extraction, comparison, review, summary) require API access.

    #### Data Privacy
    - All documents stored locally
    - Embeddings stored locally in FAISS
    - No data sent to external services except LLM query context
    - API keys via environment variables only
    """)
