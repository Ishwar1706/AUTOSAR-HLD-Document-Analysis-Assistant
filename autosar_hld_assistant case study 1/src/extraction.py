"""
Entity extraction module.

Extracts structured architecture entities (components, interfaces, signals,
dependencies) from ingested HLD documents via LLM. Implements batch processing,
JSON validation, and deduplication.
"""

import json
import logging
from typing import Dict, List, Optional

from src.vectorstore import VectorStore
from src.rag_pipeline import build_context_block
from src.llm_client import chat_completion, LLMError
from src.prompts import get_extraction_prompt

logger = logging.getLogger(__name__)

# Expected entity categories
ENTITY_CATEGORIES = ("components", "interfaces", "signals", "dependencies")


def _safe_json_parse(raw: str) -> Dict:
    """
    Safely parse LLM JSON output with fallback strategies.
    Handles common LLM output issues like markdown code blocks.
    """
    # First, try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strip markdown code blocks if present
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: locate first { ... last }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse LLM JSON response")
    return {
        "components": [], "interfaces": [], "signals": [], "dependencies": [],
        "_parse_error": True, "_raw_response": raw[:500],
    }


def _validate_entity(entity: dict, category: str) -> dict:
    """Validate and clean an extracted entity, replacing missing fields."""
    required_fields = {
        "components": ["name", "responsibility", "mapped_ecu", "source_document", "source_page"],
        "interfaces": ["port_name", "direction", "interface_type", "owning_component", "source_document", "source_page"],
        "signals": ["signal_name", "data_type", "range_or_values", "description", "source_document", "source_page"],
        "dependencies": ["component", "depends_on", "dependency_type", "source_document", "source_page"],
    }

    fields = required_fields.get(category, [])
    cleaned = {}
    for field in fields:
        value = entity.get(field, "Not specified")
        if value is None or str(value).strip() == "":
            value = "Not specified"
        cleaned[field] = str(value)

    return cleaned


def _deduplicate(merged: Dict) -> Dict:
    """Remove exact-duplicate entries that can arise from overlapping chunks."""
    deduped = {}
    for key, items in merged.items():
        if key.startswith("_"):
            continue
        seen = set()
        unique_items = []
        for item in items:
            fingerprint = json.dumps(item, sort_keys=True)
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique_items.append(item)
        deduped[key] = unique_items
    return deduped


def extract_entities(
    collection_name: str,
    doc_name: str,
    batch_size: int = 10,
) -> Dict:
    """
    Run structured extraction over an entire ingested document.
    Processes in batches of chunks for context-limit safety, then merges and deduplicates.
    """
    store = VectorStore(collection_name)
    chunks = store.chunks_for_document(doc_name)

    if not chunks:
        return {"components": [], "interfaces": [], "signals": [], "dependencies": []}

    merged = {"components": [], "interfaces": [], "signals": [], "dependencies": []}
    parse_errors = 0

    system_prompt = get_extraction_prompt()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        context_block = build_context_block(batch)
        user_prompt = f"DOCUMENT TEXT:\n{context_block}\n\nExtract the JSON as instructed."

        try:
            raw = chat_completion(
                system_prompt, user_prompt,
                json_mode=True, temperature=0.0,
            )
            parsed = _safe_json_parse(raw)

            if parsed.get("_parse_error"):
                parse_errors += 1

            for key in ENTITY_CATEGORIES:
                raw_items = parsed.get(key, [])
                for item in raw_items:
                    if isinstance(item, dict):
                        cleaned = _validate_entity(item, key)
                        merged[key].append(cleaned)

        except LLMError as e:
            logger.error(f"LLM error during extraction batch {i}: {e}")
            parse_errors += 1

    merged = _deduplicate(merged)

    # Add metadata
    merged["_metadata"] = {
        "document": doc_name,
        "total_chunks_processed": len(chunks),
        "batch_size": batch_size,
        "parse_errors": parse_errors,
        "entity_counts": {k: len(v) for k, v in merged.items() if not k.startswith("_")},
    }

    logger.info(
        f"Extraction complete for '{doc_name}': "
        f"{merged['_metadata']['entity_counts']}, "
        f"{parse_errors} parse errors"
    )

    return merged


def get_entity_counts(extraction_result: Dict) -> Dict[str, int]:
    """Get entity counts from an extraction result."""
    counts = {}
    for key in ENTITY_CATEGORIES:
        counts[key] = len(extraction_result.get(key, []))
    return counts
