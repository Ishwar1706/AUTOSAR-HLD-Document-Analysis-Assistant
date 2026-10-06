"""Tests for the extraction module."""

import sys
import json
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extraction import _safe_json_parse, _validate_entity, _deduplicate


class TestSafeJsonParse:
    def test_valid_json(self):
        raw = '{"components": [], "interfaces": [], "signals": [], "dependencies": []}'
        result = _safe_json_parse(raw)
        assert "components" in result
        assert not result.get("_parse_error")

    def test_json_with_markdown_block(self):
        raw = '```json\n{"components": [{"name": "SWC_Test"}]}\n```'
        result = _safe_json_parse(raw)
        assert "components" in result
        assert not result.get("_parse_error")

    def test_json_with_surrounding_text(self):
        raw = 'Here is the result: {"components": []} some extra text'
        result = _safe_json_parse(raw)
        assert "components" in result

    def test_invalid_json(self):
        raw = "This is not JSON at all"
        result = _safe_json_parse(raw)
        assert result.get("_parse_error") is True
        assert result["components"] == []

    def test_empty_string(self):
        result = _safe_json_parse("")
        assert result.get("_parse_error") is True


class TestValidateEntity:
    def test_complete_component(self):
        entity = {
            "name": "SWC_Test",
            "responsibility": "Testing",
            "mapped_ecu": "ECU_01",
            "source_document": "test.pdf",
            "source_page": "3",
        }
        result = _validate_entity(entity, "components")
        assert result["name"] == "SWC_Test"
        assert result["mapped_ecu"] == "ECU_01"

    def test_missing_fields_filled(self):
        entity = {"name": "SWC_Test"}
        result = _validate_entity(entity, "components")
        assert result["responsibility"] == "Not specified"
        assert result["mapped_ecu"] == "Not specified"

    def test_none_values_replaced(self):
        entity = {"name": "SWC_Test", "responsibility": None, "mapped_ecu": ""}
        result = _validate_entity(entity, "components")
        assert result["responsibility"] == "Not specified"
        assert result["mapped_ecu"] == "Not specified"

    def test_signal_validation(self):
        entity = {"signal_name": "TestSignal", "data_type": "uint8"}
        result = _validate_entity(entity, "signals")
        assert result["signal_name"] == "TestSignal"
        assert result["data_type"] == "uint8"
        assert result["range_or_values"] == "Not specified"


class TestDeduplicate:
    def test_removes_duplicates(self):
        merged = {
            "components": [
                {"name": "SWC_A", "source_page": "1"},
                {"name": "SWC_A", "source_page": "1"},
                {"name": "SWC_B", "source_page": "2"},
            ]
        }
        result = _deduplicate(merged)
        assert len(result["components"]) == 2

    def test_keeps_unique(self):
        merged = {
            "components": [
                {"name": "SWC_A"},
                {"name": "SWC_B"},
                {"name": "SWC_C"},
            ]
        }
        result = _deduplicate(merged)
        assert len(result["components"]) == 3

    def test_empty_list(self):
        merged = {"components": []}
        result = _deduplicate(merged)
        assert result["components"] == []

    def test_skips_metadata_keys(self):
        merged = {"components": [], "_metadata": {"key": "value"}}
        result = _deduplicate(merged)
        assert "_metadata" not in result
