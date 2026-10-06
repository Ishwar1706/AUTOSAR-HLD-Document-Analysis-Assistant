"""
Prompt management module.

Loads prompt templates from external files in Model_Prompts_Config/
for versioning and transparency. Falls back to embedded defaults
if files are missing.
"""

import logging
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Embedded fallback prompts (used if external files are missing)
_FALLBACK_PROMPTS = {
    "rag": (
        "You are an AUTOSAR HLD Document Analysis Assistant.\n\n"
        "Answer ONLY using the CONTEXT provided. Cite sources as "
        "[Source: <document>, Page <page>]. If evidence is insufficient, "
        "say so clearly. Do not invent information."
    ),
    "extraction": (
        "You are an AUTOSAR architecture extraction engine.\n\n"
        "Extract structured JSON with components, interfaces, signals, "
        "and dependencies. Only extract explicitly stated information."
    ),
    "comparison": (
        "You are an AUTOSAR HLD document comparison assistant.\n\n"
        "Compare two sets of architecture data and report additions, "
        "removals, modifications, and potential inconsistencies."
    ),
    "review": (
        "You are an AUTOSAR HLD architecture review assistant.\n\n"
        "Check for potential issues: undefined references, missing definitions, "
        "naming inconsistencies. Return JSON with potential_issues array."
    ),
    "summary": (
        "You are an AUTOSAR HLD document summarization assistant.\n\n"
        "Produce a structured summary covering purpose, components, interfaces, "
        "signals, dependencies, and open points. Cite sources."
    ),
}


def load_prompt(prompt_name: str, version: str = "v1") -> str:
    """
    Load a prompt template from Model_Prompts_Config/<name>_prompt_<version>.txt.
    Falls back to embedded default if file is missing.
    """
    filename = f"{prompt_name}_prompt_{version}.txt"
    filepath = config.PROMPTS_DIR / filename

    if filepath.exists():
        try:
            content = filepath.read_text(encoding="utf-8").strip()
            if content:
                logger.debug(f"Loaded prompt from {filepath}")
                return content
        except Exception as e:
            logger.warning(f"Error reading prompt file {filepath}: {e}")

    # Fallback to embedded prompt
    fallback = _FALLBACK_PROMPTS.get(prompt_name, "")
    if fallback:
        logger.debug(f"Using fallback prompt for '{prompt_name}'")
        return fallback

    raise ValueError(f"No prompt found for '{prompt_name}' version '{version}'")


def get_rag_prompt() -> str:
    """Load the RAG system prompt."""
    return load_prompt("rag")


def get_extraction_prompt() -> str:
    """Load the entity extraction prompt."""
    return load_prompt("extraction")


def get_comparison_prompt() -> str:
    """Load the document comparison prompt."""
    return load_prompt("comparison")


def get_review_prompt() -> str:
    """Load the architecture review prompt."""
    return load_prompt("review")


def get_summary_prompt() -> str:
    """Load the document summary prompt."""
    return load_prompt("summary")


def list_available_prompts() -> list:
    """List all available prompt files."""
    prompts = []
    if config.PROMPTS_DIR.exists():
        for f in sorted(config.PROMPTS_DIR.glob("*_prompt_*.txt")):
            prompts.append({
                "name": f.stem,
                "file": f.name,
                "size_bytes": f.stat().st_size,
            })
    return prompts
