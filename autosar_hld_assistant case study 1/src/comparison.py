"""
Document comparison module.

Compares two ingested documents (e.g. HLD v1.0 vs v1.1) by extracting
entities from both and asking the LLM to report differences — added,
removed, modified elements, and potential inconsistencies.
"""

import json
import logging
from typing import Dict, Optional

from src.extraction import extract_entities
from src.llm_client import chat_completion, LLMError
from src.prompts import get_comparison_prompt

logger = logging.getLogger(__name__)


def compare_documents(
    collection_name: str,
    doc_a: str,
    doc_b: str,
    entities_a: Optional[Dict] = None,
    entities_b: Optional[Dict] = None,
) -> Dict:
    """
    Compare two documents and return a structured comparison report.

    If pre-extracted entities are provided, uses those directly;
    otherwise extracts from both documents first.

    Returns a dict with the LLM report text and structured change summary.
    """
    # Extract entities if not provided
    if entities_a is None:
        entities_a = extract_entities(collection_name, doc_a)
    if entities_b is None:
        entities_b = extract_entities(collection_name, doc_b)

    # Build comparison prompt
    system_prompt = get_comparison_prompt()
    user_prompt = (
        f"DOCUMENT A ({doc_a}) EXTRACTED DATA:\n{json.dumps(_strip_metadata(entities_a), indent=2)}\n\n"
        f"DOCUMENT B ({doc_b}) EXTRACTED DATA:\n{json.dumps(_strip_metadata(entities_b), indent=2)}\n\n"
        "Compare Document A and Document B as instructed."
    )

    try:
        report_text = chat_completion(system_prompt, user_prompt, temperature=0.1)
    except LLMError as e:
        report_text = f"LLM service unavailable for comparison: {e}"

    # Build a programmatic change summary
    change_summary = _compute_change_summary(entities_a, entities_b)

    return {
        "doc_a": doc_a,
        "doc_b": doc_b,
        "report": report_text,
        "change_summary": change_summary,
        "entities_a_counts": {k: len(v) for k, v in entities_a.items() if not k.startswith("_")},
        "entities_b_counts": {k: len(v) for k, v in entities_b.items() if not k.startswith("_")},
    }


def _strip_metadata(entities: Dict) -> Dict:
    """Remove internal metadata keys from entities dict for LLM prompt."""
    return {k: v for k, v in entities.items() if not k.startswith("_")}


def _compute_change_summary(entities_a: Dict, entities_b: Dict) -> Dict:
    """
    Compute a basic programmatic change summary by comparing entity names.
    This supplements the LLM's qualitative comparison with quantitative data.
    """
    summary = {}

    name_keys = {
        "components": "name",
        "interfaces": "port_name",
        "signals": "signal_name",
        "dependencies": "component",
    }

    for category, name_key in name_keys.items():
        items_a = entities_a.get(category, [])
        items_b = entities_b.get(category, [])

        names_a = {item.get(name_key, "").strip().lower() for item in items_a if isinstance(item, dict)}
        names_b = {item.get(name_key, "").strip().lower() for item in items_b if isinstance(item, dict)}

        # Filter out empty/not-specified names
        names_a = {n for n in names_a if n and n != "not specified"}
        names_b = {n for n in names_b if n and n != "not specified"}

        added = names_b - names_a
        removed = names_a - names_b
        common = names_a & names_b

        summary[category] = {
            "in_doc_a": len(names_a),
            "in_doc_b": len(names_b),
            "added": sorted(added),
            "removed": sorted(removed),
            "common": len(common),
            "change_type": _classify_change(added, removed),
        }

    return summary


def _classify_change(added: set, removed: set) -> str:
    """Classify the type of change for a category."""
    if not added and not removed:
        return "Unchanged"
    elif added and not removed:
        return "Added"
    elif removed and not added:
        return "Removed"
    else:
        return "Modified"


def format_comparison_table(change_summary: Dict) -> list:
    """
    Format the change summary as a list of dicts suitable for a table display.
    """
    rows = []
    for category, changes in change_summary.items():
        if changes.get("added"):
            for item in changes["added"]:
                rows.append({
                    "Category": category.title(),
                    "Change": "Added",
                    "Item": item,
                    "In Doc A": "No",
                    "In Doc B": "Yes",
                })
        if changes.get("removed"):
            for item in changes["removed"]:
                rows.append({
                    "Category": category.title(),
                    "Change": "Removed",
                    "Item": item,
                    "In Doc A": "Yes",
                    "In Doc B": "No",
                })
        if not changes.get("added") and not changes.get("removed"):
            rows.append({
                "Category": category.title(),
                "Change": "No changes detected",
                "Item": f"{changes.get('common', 0)} items in common",
                "In Doc A": str(changes.get("in_doc_a", 0)),
                "In Doc B": str(changes.get("in_doc_b", 0)),
            })
    return rows
