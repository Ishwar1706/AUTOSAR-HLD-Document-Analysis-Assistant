"""
Utility functions for the AUTOSAR HLD Document Analysis Assistant.
"""

import json
import csv
import io
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def export_entities_json(entities: Dict, doc_name: str = "") -> str:
    """Export extracted entities as formatted JSON string."""
    export_data = {
        "export_timestamp": datetime.utcnow().isoformat(),
        "source_document": doc_name,
        "disclaimer": "AI-extracted data — requires engineering review before use.",
        "components": entities.get("components", []),
        "interfaces": entities.get("interfaces", []),
        "signals": entities.get("signals", []),
        "dependencies": entities.get("dependencies", []),
    }
    return json.dumps(export_data, indent=2)


def export_entities_csv(items: List[Dict], category: str) -> str:
    """Export a list of entity dicts as a CSV string."""
    if not items:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=items[0].keys())
    writer.writeheader()
    writer.writerows(items)
    return output.getvalue()


def export_comparison_csv(comparison_result: Dict) -> str:
    """Export comparison results as CSV."""
    from src.comparison import format_comparison_table
    rows = format_comparison_table(comparison_result.get("change_summary", {}))
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_issues_csv(review_result: Dict) -> str:
    """Export review issues as CSV."""
    issues = review_result.get("potential_issues", [])
    if not issues:
        return ""
    output = io.StringIO()
    fieldnames = ["issue_id", "category", "severity", "description", "evidence",
                  "source_document", "source_page", "recommendation"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(issues)
    return output.getvalue()


def generate_analysis_report(
    project_name: str,
    stats: Dict,
    extractions: Dict[str, Dict] = None,
    review_results: Dict[str, Dict] = None,
) -> str:
    """Generate a structured text report summarizing the project analysis."""
    lines = [
        "=" * 70,
        "AUTOSAR HLD DOCUMENT ANALYSIS REPORT",
        "=" * 70,
        f"Project: {project_name}",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "DISCLAIMER: This is an AI-generated analysis report.",
        "All findings require human engineering review before use in",
        "design, compliance, release, or validation decisions.",
        "",
        "-" * 70,
        "PROJECT SUMMARY",
        "-" * 70,
        f"Total documents: {stats.get('total_documents', 0)}",
        f"Total chunks indexed: {stats.get('total_chunks', 0)}",
        f"Documents: {', '.join(stats.get('documents', []))}",
        "",
    ]

    if extractions:
        lines.append("-" * 70)
        lines.append("ENTITY EXTRACTION SUMMARY")
        lines.append("-" * 70)
        for doc_name, entities in extractions.items():
            lines.append(f"\n  Document: {doc_name}")
            for cat in ("components", "interfaces", "signals", "dependencies"):
                count = len(entities.get(cat, []))
                lines.append(f"    {cat.title()}: {count}")

    if review_results:
        lines.append("")
        lines.append("-" * 70)
        lines.append("POTENTIAL ISSUES SUMMARY")
        lines.append("-" * 70)
        for doc_name, review in review_results.items():
            summary = review.get("summary", {})
            lines.append(f"\n  Document: {doc_name}")
            lines.append(f"    Total potential issues: {summary.get('total_issues', 0)}")
            lines.append(f"    High severity: {summary.get('high_severity', 0)}")
            lines.append(f"    Medium severity: {summary.get('medium_severity', 0)}")
            lines.append(f"    Low severity: {summary.get('low_severity', 0)}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)

    return "\n".join(lines)


# Demo / sample questions
SAMPLE_QUESTIONS = [
    "What signals does SWC_DoorLockControl use?",
    "What is the functional flow for contactor closing in the BMS?",
    "What are the main components of the BCM architecture?",
    "What interfaces are used by the ADAS FCW system?",
    "What is the responsibility of SWC_CollisionRiskEstimator?",
    "What are the dependencies of SWC_WindowLiftSupervisor?",
    "What data type is the CellVoltageValidated signal?",
    "What ECU is SWC_CellBalancingController mapped to?",
    "What changed between BMS v1.0 and v1.1?",
    "What are the open points in the BCM HLD?",
]
