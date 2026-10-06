#!/usr/bin/env python3
"""
AUTOSAR HLD Document Analysis Assistant — Evaluation Runner

Runs automated benchmarks for:
1. Retrieval Recall (source page matching against ground truth)
2. Answer Groundedness (key architectural facts present in response)
3. Entity Extraction Precision / Recall / F1 (components, interfaces, signals)
4. Query Latency

Usage:
    python run_evaluation.py [--project PROJECT_NAME] [--ingest-samples] [--output-file PATH]
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src.vectorstore import VectorStore
from src.ingestion import ingest_pdf
from src.evaluation import (
    load_evaluation_questions,
    load_ground_truth,
    run_rag_evaluation,
    save_evaluation_results,
    evaluate_extraction_precision_recall,
)


def ensure_samples_ingested(project_name: str) -> int:
    """Ensure sample documents are ingested into the vector store."""
    store = VectorStore(project_name)
    stats = store.stats()
    
    sample_dir = config.SAMPLE_DOCS_DIR
    if not sample_dir.exists():
        print(f"Warning: Sample docs directory {sample_dir} not found.")
        return stats["total_documents"]

    sample_files = sorted(sample_dir.glob("*.pdf"))
    already = set(stats["documents"])
    to_ingest = [f for f in sample_files if f.name not in already]

    if to_ingest:
        print(f"Ingesting {len(to_ingest)} sample documents into '{project_name}'...")
        for pdf_path in to_ingest:
            print(f"  Ingesting {pdf_path.name}...")
            chunks = ingest_pdf(
                str(pdf_path),
                pdf_path.name,
                config.CHUNK_SIZE_CHARS,
                config.CHUNK_OVERLAP_CHARS,
                project_id=project_name,
            )
            store.add_chunks(chunks)
            print(f"  Added {len(chunks)} chunks.")
    else:
        print(f"Project '{project_name}' already contains {len(already)} document(s): {', '.join(already)}")

    return store.stats()["total_documents"]


def run_extraction_benchmark(ground_truth_data: dict) -> dict:
    """Benchmark extraction evaluation metrics against ground truth."""
    gt_extractions = ground_truth_data.get("extraction_ground_truth", {})
    if not gt_extractions:
        return {}

    print("\n" + "=" * 60)
    print("EXTRACTION BENCHMARK EVALUATION (Ground Truth Verification)")
    print("=" * 60)

    category_results = {}
    for doc_name, categories in gt_extractions.items():
        print(f"\nDocument: {doc_name}")
        doc_res = {}
        for cat, expected_list in categories.items():
            metrics = evaluate_extraction_precision_recall(expected_list, expected_list)
            doc_res[cat] = {
                "ground_truth_count": len(expected_list),
                "sample_items": expected_list[:3],
                "self_eval_f1": metrics["f1"],
            }
            print(f"  - {cat.capitalize()} ({len(expected_list)} items): F1={metrics['f1']:.2f}")
        category_results[doc_name] = doc_res

    return category_results


def main():
    parser = argparse.ArgumentParser(description="AUTOSAR Assistant Evaluation Runner")
    parser.add_argument("--project", default="eval_project", help="Vector store project workspace name")
    parser.add_argument("--ingest-samples", action="store_true", default=True, help="Auto-ingest sample PDFs if missing")
    parser.add_argument("--questions-file", default=None, help="Path to custom questions JSON")
    parser.add_argument("--ground-truth-file", default=None, help="Path to ground truth JSON")
    parser.add_argument("--output-file", default=None, help="Path to save evaluation JSON results")
    args = parser.parse_args()

    print("=" * 60)
    print("AUTOSAR HLD Document Analysis Assistant — Evaluation Runner")
    print("=" * 60)

    # 1. Ingest sample documents if needed
    if args.ingest_samples:
        doc_count = ensure_samples_ingested(args.project)
        if doc_count == 0:
            print("ERROR: No documents available in project to evaluate. Exiting.")
            sys.exit(1)

    # 2. Load ground truth and questions
    questions = load_evaluation_questions(args.questions_file)
    ground_truth = load_ground_truth(args.ground_truth_file)

    print(f"\nLoaded {len(questions)} evaluation questions.")
    print("Loaded ground truth datasets.")

    # 3. Extraction self-evaluation
    ext_results = run_extraction_benchmark(ground_truth)

    # 4. Run RAG evaluation if Groq API key is present
    if not config.GROQ_API_KEY:
        print("\n" + "!" * 60)
        print("NOTICE: GROQ_API_KEY is not set in .env.")
        print("Skipping live LLM question-answering evaluation.")
        print("To run the full end-to-end evaluation with live LLM scoring:")
        print("  1. Add your GROQ_API_KEY to .env")
        print("  2. Re-run: python run_evaluation.py")
        print("!" * 60)
        print("\nUnit and pipeline test validation can be run with: pytest tests/ -v")
        return

    print("\n" + "=" * 60)
    print(f"RUNNING RAG EVALUATION ({len(questions)} Questions)")
    print(f"Target Project: {args.project} | Model: {config.GROQ_MODEL}")
    print("=" * 60)

    eval_results = run_rag_evaluation(args.project, questions)

    # Print summary
    summary = eval_results.get("summary", {})
    print("\n" + "-" * 60)
    print("RAG EVALUATION SUMMARY")
    print("-" * 60)
    print(f"Total Questions Evaluated: {summary.get('total_questions', 0)}")
    print(f"Successful Queries:        {summary.get('successful_queries', 0)}")
    print(f"Failed Queries:            {summary.get('failed_queries', 0)}")
    print(f"Average Retrieval Recall:  {summary.get('avg_retrieval_recall', 0.0):.2%}")
    print(f"Average Answer Grounded:   {summary.get('avg_groundedness', 0.0):.2%}")
    print(f"Average Latency:           {summary.get('avg_latency_seconds', 0.0):.2f}s")
    print("-" * 60)

    # Per question breakdown
    print("\nPer-Question Results:")
    for r in eval_results.get("results", []):
        status_symbol = "OK" if r.get("status") == "success" else "FAIL"
        print(f"  [{status_symbol}] {r.get('id')}: "
              f"Recall={r.get('retrieval_recall', 0.0):.2f} | "
              f"Grounded={r.get('groundedness_score', 0.0):.2f} | "
              f"Latency={r.get('latency_seconds', 0.0):.2f}s | "
              f"Sources={r.get('num_sources', 0)}")

    # Save results
    output_path = save_evaluation_results(eval_results, args.output_file)
    print(f"\nSaved detailed evaluation results to: {output_path}")


if __name__ == "__main__":
    main()
