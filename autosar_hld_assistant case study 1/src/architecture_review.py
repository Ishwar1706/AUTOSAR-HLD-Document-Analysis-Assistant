"""
Architecture review module.

AI-assisted architecture review that checks for potential issues:
- Undefined references
- Missing definitions
- Orphan dependencies
- Naming inconsistencies
- Missing information
- Contradictions

All findings are labeled as POTENTIAL issues requiring human review.
"""

import json
import logging
from typing import Dict, List, Optional

from src.extraction import extract_entities, ENTITY_CATEGORIES
from src.llm_client import chat_completion, LLMError
from src.prompts import get_review_prompt

logger = logging.getLogger(__name__)


def _safe_json_parse_review(raw: str) -> Dict:
    """Parse the review JSON output from the LLM."""
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strip markdown blocks
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

    # Find JSON block
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    return {"potential_issues": [], "_parse_error": True}


def _run_programmatic_checks(entities: Dict, doc_name: str) -> List[Dict]:
    """
    Run rule-based checks on extracted entities that don't require LLM.
    These are deterministic and reproducible.
    """
    issues = []
    issue_counter = 0

    components = entities.get("components", [])
    interfaces = entities.get("interfaces", [])
    signals = entities.get("signals", [])
    dependencies = entities.get("dependencies", [])

    # Get all component names
    component_names = {
        c.get("name", "").strip().lower()
        for c in components
        if c.get("name") and c.get("name") != "Not specified"
    }

    # Check 1: Dependencies referencing undefined components
    for dep in dependencies:
        depends_on = dep.get("depends_on", "").strip()
        if depends_on and depends_on != "Not specified":
            # Check each dependency target (may be comma-separated)
            targets = [t.strip() for t in depends_on.split(",")]
            for target in targets:
                target_lower = target.lower().strip()
                # Skip BSW modules (they're expected external dependencies)
                if target_lower.startswith("bsw_"):
                    continue
                if target_lower and target_lower not in component_names:
                    issue_counter += 1
                    issues.append({
                        "issue_id": f"PRG-{issue_counter:03d}",
                        "category": "orphan_dependency",
                        "severity": "medium",
                        "description": f"Dependency target '{target}' is not found in the extracted component list.",
                        "evidence": f"Component '{dep.get('component')}' depends on '{target}', but '{target}' is not listed as a defined component.",
                        "source_document": doc_name,
                        "source_page": dep.get("source_page", "Not specified"),
                        "recommendation": "Verify if this dependency target is defined elsewhere or is a BSW/external module.",
                    })

    # Check 2: Interfaces with missing owning component
    for iface in interfaces:
        owner = iface.get("owning_component", "").strip()
        if owner and owner != "Not specified":
            if owner.lower() not in component_names:
                issue_counter += 1
                issues.append({
                    "issue_id": f"PRG-{issue_counter:03d}",
                    "category": "undefined_reference",
                    "severity": "medium",
                    "description": f"Interface '{iface.get('port_name')}' references component '{owner}' which is not in the component list.",
                    "evidence": f"Port '{iface.get('port_name')}' is owned by '{owner}', but this component was not extracted.",
                    "source_document": doc_name,
                    "source_page": iface.get("source_page", "Not specified"),
                    "recommendation": "Check if the owning component is defined in the document but was not extracted.",
                })

    # Check 3: Missing information (fields with "Not specified")
    not_specified_counts = {"components": 0, "interfaces": 0, "signals": 0, "dependencies": 0}
    for category in ENTITY_CATEGORIES:
        items = entities.get(category, [])
        for item in items:
            ns_fields = [k for k, v in item.items() if v == "Not specified" and k not in ("source_page", "source_document")]
            if ns_fields:
                not_specified_counts[category] += 1

    for category, count in not_specified_counts.items():
        if count > 0:
            issue_counter += 1
            issues.append({
                "issue_id": f"PRG-{issue_counter:03d}",
                "category": "missing_information",
                "severity": "low",
                "description": f"{count} {category} entries have incomplete field values ('Not specified').",
                "evidence": f"Out of {len(entities.get(category, []))} extracted {category}, {count} have one or more fields marked as 'Not specified'.",
                "source_document": doc_name,
                "source_page": "Multiple",
                "recommendation": f"Review the document to determine if missing {category} information should be added.",
            })

    # Check 4: Components with no interfaces
    components_with_interfaces = {
        iface.get("owning_component", "").strip().lower()
        for iface in interfaces
        if iface.get("owning_component")
    }
    for comp in components:
        comp_name = comp.get("name", "").strip()
        if comp_name and comp_name.lower() not in components_with_interfaces:
            issue_counter += 1
            issues.append({
                "issue_id": f"PRG-{issue_counter:03d}",
                "category": "missing_definition",
                "severity": "low",
                "description": f"Component '{comp_name}' has no interfaces defined in the extraction.",
                "evidence": f"No ports/interfaces were found with owning_component = '{comp_name}'.",
                "source_document": doc_name,
                "source_page": comp.get("source_page", "Not specified"),
                "recommendation": "Check if this component's interfaces are defined elsewhere in the document.",
            })

    return issues


def review_architecture(
    collection_name: str,
    doc_name: str,
    entities: Optional[Dict] = None,
    use_llm: bool = True,
) -> Dict:
    """
    Run an AI-assisted architecture review on extracted entities.

    Combines programmatic checks (deterministic) with LLM-based analysis
    (when available) for comprehensive coverage.
    """
    # Extract entities if not provided
    if entities is None:
        entities = extract_entities(collection_name, doc_name)

    all_issues = []

    # Step 1: Programmatic checks (always available, no LLM needed)
    programmatic_issues = _run_programmatic_checks(entities, doc_name)
    all_issues.extend(programmatic_issues)

    # Step 2: LLM-based review (if available and requested)
    llm_issues = []
    llm_error = None
    if use_llm:
        try:
            system_prompt = get_review_prompt()
            entities_clean = {k: v for k, v in entities.items() if not k.startswith("_")}
            user_prompt = (
                f"DOCUMENT: {doc_name}\n\n"
                f"EXTRACTED ARCHITECTURE DATA:\n{json.dumps(entities_clean, indent=2)}\n\n"
                "Analyze this architecture data for potential issues as instructed."
            )
            raw = chat_completion(system_prompt, user_prompt, json_mode=True, temperature=0.0)
            parsed = _safe_json_parse_review(raw)

            for issue in parsed.get("potential_issues", []):
                if isinstance(issue, dict):
                    # Prefix LLM issue IDs to distinguish from programmatic
                    issue["issue_id"] = f"LLM-{issue.get('issue_id', 'unknown')}"
                    llm_issues.append(issue)

        except LLMError as e:
            llm_error = str(e)
            logger.warning(f"LLM review unavailable: {e}")

    all_issues.extend(llm_issues)

    # Compute summary
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for issue in all_issues:
        sev = issue.get("severity", "low").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1

    return {
        "document": doc_name,
        "potential_issues": all_issues,
        "summary": {
            "total_issues": len(all_issues),
            "programmatic_issues": len(programmatic_issues),
            "llm_issues": len(llm_issues),
            "high_severity": severity_counts["high"],
            "medium_severity": severity_counts["medium"],
            "low_severity": severity_counts["low"],
        },
        "llm_available": llm_error is None,
        "llm_error": llm_error,
        "entity_counts": {k: len(v) for k, v in entities.items() if not k.startswith("_")},
    }
