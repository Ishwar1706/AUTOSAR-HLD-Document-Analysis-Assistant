"""Tests for the comparison module."""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.comparison import _compute_change_summary, _classify_change, format_comparison_table


class TestChangeClassification:
    def test_unchanged(self):
        assert _classify_change(set(), set()) == "Unchanged"

    def test_added(self):
        assert _classify_change({"a", "b"}, set()) == "Added"

    def test_removed(self):
        assert _classify_change(set(), {"a"}) == "Removed"

    def test_modified(self):
        assert _classify_change({"a"}, {"b"}) == "Modified"


class TestChangeSummary:
    def test_identical_entities(self):
        entities = {
            "components": [{"name": "SWC_A"}],
            "interfaces": [{"port_name": "PPort_X"}],
            "signals": [{"signal_name": "Sig1"}],
            "dependencies": [{"component": "SWC_A"}],
        }
        summary = _compute_change_summary(entities, entities)
        for category in summary.values():
            assert category["added"] == []
            assert category["removed"] == []

    def test_added_component(self):
        a = {"components": [{"name": "SWC_A"}], "interfaces": [], "signals": [], "dependencies": []}
        b = {"components": [{"name": "SWC_A"}, {"name": "SWC_B"}], "interfaces": [], "signals": [], "dependencies": []}
        summary = _compute_change_summary(a, b)
        assert "swc_b" in summary["components"]["added"]

    def test_removed_component(self):
        a = {"components": [{"name": "SWC_A"}, {"name": "SWC_B"}], "interfaces": [], "signals": [], "dependencies": []}
        b = {"components": [{"name": "SWC_A"}], "interfaces": [], "signals": [], "dependencies": []}
        summary = _compute_change_summary(a, b)
        assert "swc_b" in summary["components"]["removed"]

    def test_empty_entities(self):
        empty = {"components": [], "interfaces": [], "signals": [], "dependencies": []}
        summary = _compute_change_summary(empty, empty)
        for category in summary.values():
            assert category["change_type"] == "Unchanged"

    def test_not_specified_filtered(self):
        a = {"components": [{"name": "Not specified"}], "interfaces": [], "signals": [], "dependencies": []}
        b = {"components": [], "interfaces": [], "signals": [], "dependencies": []}
        summary = _compute_change_summary(a, b)
        assert summary["components"]["in_doc_a"] == 0  # "Not specified" filtered out


class TestComparisonTable:
    def test_format_with_changes(self):
        summary = {
            "components": {
                "in_doc_a": 2, "in_doc_b": 3,
                "added": ["swc_new"], "removed": [],
                "common": 2, "change_type": "Added",
            },
            "interfaces": {
                "in_doc_a": 3, "in_doc_b": 3,
                "added": [], "removed": [],
                "common": 3, "change_type": "Unchanged",
            },
        }
        rows = format_comparison_table(summary)
        assert len(rows) >= 2
        # Check that added item is in the table
        added_rows = [r for r in rows if r.get("Change") == "Added"]
        assert len(added_rows) >= 1

    def test_format_empty_summary(self):
        rows = format_comparison_table({})
        assert rows == []
