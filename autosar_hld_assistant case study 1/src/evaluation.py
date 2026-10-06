"""
Evaluation module for the AUTOSAR HLD Document Analysis Assistant.

Provides:
- Benchmark dataset loading
- RAG evaluation (retrieval recall, answer quality)
- Extraction evaluation (precision/recall/F1)
- Result export and reporting
"""

import json
import time
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

import config

logger = logging.getLogger(__name__)


def load_evaluation_questions(filepath: Optional[str] = None) -> List[Dict]:
    """Load the evaluation question set from JSON."""
    if filepath is None:
        filepath = config.BASE_DIR / "evaluation" / "questions.json"
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        logger.warning(f"Evaluation questions file not found: {filepath}")
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("questions", [])
    except Exception as e:
        logger.error(f"Error loading evaluation questions: {e}")
        return []


def load_ground_truth(filepath: Optional[str] = None) -> Dict:
    """Load ground truth data for evaluation."""
    if filepath is None:
        filepath = config.BASE_DIR / "evaluation" / "ground_truth.json"
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        logger.warning(f"Ground truth file not found: {filepath}")
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading ground truth: {e}")
        return {}


def evaluate_retrieval_recall(
    retrieved_pages: List[int],
    expected_pages: List[int],
) -> float:
    """
    Calculate retrieval recall: what fraction of expected source pages
    were found in the retrieved chunks.
    """
    if not expected_pages:
        return 1.0  # No expected pages means nothing to miss
    if not retrieved_pages:
        return 0.0

    expected_set = set(expected_pages)
    retrieved_set = set(retrieved_pages)
    hits = expected_set & retrieved_set

    return len(hits) / len(expected_set)


def evaluate_answer_groundedness(
    answer: str,
    expected_points: List[str],
) -> Dict:
    """
    Check how many expected answer points are mentioned in the answer.
    Uses simple keyword/phrase matching (not LLM-based, for reproducibility).
    """
    if not expected_points:
        return {"score": 1.0, "matched": 0, "total": 0, "details": []}

    matched = 0
    details = []

    for point in expected_points:
        # Simple case-insensitive substring check
        found = point.lower() in answer.lower()
        if found:
            matched += 1
        details.append({"point": point, "found": found})

    score = matched / len(expected_points)
    return {
        "score": score,
        "matched": matched,
        "total": len(expected_points),
        "details": details,
    }


def evaluate_extraction_precision_recall(
    extracted: List[str],
    ground_truth: List[str],
) -> Dict:
    """
    Calculate precision, recall, and F1 for entity extraction.
    Uses case-insensitive comparison.
    """
    if not ground_truth and not extracted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not ground_truth:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}
    if not extracted:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    gt_set = {item.strip().lower() for item in ground_truth}
    ex_set = {item.strip().lower() for item in extracted}

    true_positives = len(gt_set & ex_set)
    precision = true_positives / len(ex_set) if ex_set else 0.0
    recall = true_positives / len(gt_set) if gt_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": true_positives,
        "false_positives": len(ex_set - gt_set),
        "false_negatives": len(gt_set - ex_set),
    }


def run_rag_evaluation(
    collection_name: str,
    questions: List[Dict],
) -> Dict:
    """
    Run the full RAG evaluation pipeline.

    For each question:
    1. Query the RAG pipeline
    2. Evaluate retrieval recall
    3. Evaluate answer groundedness
    4. Measure latency
    """
    from src.rag_pipeline import answer_question

    results = []
    total_recall = 0.0
    total_groundedness = 0.0
    total_latency = 0.0
    successful = 0
    failed = 0

    for q in questions:
        q_id = q.get("id", "unknown")
        question_text = q.get("question", "")
        expected_pages = [p.get("page", 0) for p in q.get("expected_sources", [])]
        expected_points = q.get("expected_answer_points", [])
        q_type = q.get("type", "general")
        doc_filter = q.get("document", None)

        try:
            start = time.time()
            result = answer_question(collection_name, question_text, doc_filter=doc_filter)
            latency = time.time() - start

            # Get retrieved pages
            retrieved_pages = [c.page_number for c in result.sources]

            # Calculate metrics
            recall = evaluate_retrieval_recall(retrieved_pages, expected_pages)
            groundedness = evaluate_answer_groundedness(result.answer, expected_points)

            total_recall += recall
            total_groundedness += groundedness["score"]
            total_latency += latency
            successful += 1

            results.append({
                "id": q_id,
                "question": question_text,
                "type": q_type,
                "answer": result.answer,
                "expected_pages": expected_pages,
                "retrieved_pages": sorted(set(retrieved_pages)),
                "retrieval_recall": round(recall, 4),
                "groundedness_score": round(groundedness["score"], 4),
                "groundedness_details": groundedness["details"],
                "num_sources": len(result.sources),
                "latency_seconds": round(latency, 3),
                "status": "success",
                "is_grounded": result.grounded,
            })

        except Exception as e:
            failed += 1
            results.append({
                "id": q_id,
                "question": question_text,
                "type": q_type,
                "status": "error",
                "error": str(e),
            })

    n = max(successful, 1)
    summary = {
        "total_questions": len(questions),
        "successful": successful,
        "failed": failed,
        "avg_retrieval_recall": round(total_recall / n, 4),
        "avg_groundedness": round(total_groundedness / n, 4),
        "avg_latency_seconds": round(total_latency / n, 3),
        "timestamp": datetime.utcnow().isoformat(),
        "collection": collection_name,
    }

    return {"summary": summary, "results": results}


def save_evaluation_results(
    eval_results: Dict,
    output_dir: Optional[str] = None,
):
    """Save evaluation results to JSON and CSV files."""
    if output_dir is None:
        output_dir = config.BASE_DIR / "evaluation" / "results"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full results as JSON
    json_path = output_dir / "evaluation_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    # Save summary as CSV
    import csv
    csv_path = output_dir / "evaluation_report.csv"
    results = eval_results.get("results", [])
    if results:
        fieldnames = ["id", "question", "type", "status", "retrieval_recall",
                      "groundedness_score", "num_sources", "latency_seconds"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)

    # Save summary markdown
    summary = eval_results.get("summary", {})
    md_path = output_dir / "evaluation_summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Evaluation Summary\n\n")
        f.write(f"**Date**: {summary.get('timestamp', 'N/A')}\n\n")
        f.write(f"**Collection**: {summary.get('collection', 'N/A')}\n\n")
        f.write("## Results\n\n")
        f.write(f"| Metric | Value |\n|---|---|\n")
        f.write(f"| Total Questions | {summary.get('total_questions', 0)} |\n")
        f.write(f"| Successful | {summary.get('successful', 0)} |\n")
        f.write(f"| Failed | {summary.get('failed', 0)} |\n")
        f.write(f"| Avg Retrieval Recall | {summary.get('avg_retrieval_recall', 'N/A')} |\n")
        f.write(f"| Avg Groundedness | {summary.get('avg_groundedness', 'N/A')} |\n")
        f.write(f"| Avg Latency (s) | {summary.get('avg_latency_seconds', 'N/A')} |\n")
        f.write(f"\n> These metrics are calculated from automated evaluation.\n")
        f.write(f"> Human evaluation should supplement these results.\n")

    logger.info(f"Evaluation results saved to {output_dir}")
    return {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path)}
