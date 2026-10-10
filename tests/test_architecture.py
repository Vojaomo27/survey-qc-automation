"""Smoke tests for the Phase 1 architecture.

These verify that the foundational layers import cleanly, configuration loads
and merges correctly, and the rule registry mechanism works. They intentionally
avoid GUI, Excel and database concerns (added in later phases).
"""

from __future__ import annotations

from config.config_manager import ConfigManager, _deep_merge
from core.canonical_fields import CANONICAL_FIELD_MAP, field_keys, get_field
from core.models import ColumnMapping, RuleResult
from rules.base_rule import RULE_REGISTRY, BaseRule


def test_config_loads_defaults() -> None:
    """Configuration loads with the expected default threshold values."""
    config = ConfigManager()
    assert config.get_threshold("min_interview_duration") == 35
    assert config.get_threshold("max_interview_duration") == 120
    assert config.get_setting("appearance_mode") == "System"


def test_deep_merge_overrides_nested_values() -> None:
    """User overrides win over defaults without dropping unspecified keys."""
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    override = {"a": {"y": 20}}
    merged = _deep_merge(base, override)
    assert merged == {"a": {"x": 1, "y": 20}, "b": 3}
    assert base["a"]["y"] == 2  # original is untouched


def test_canonical_fields_registry() -> None:
    """Canonical field registry is consistent and queryable."""
    keys = field_keys()
    assert "instance_id" in keys
    assert get_field("enumerator").label == "Enumerator"
    assert len(keys) == len(CANONICAL_FIELD_MAP)


def test_column_mapping_helpers() -> None:
    """ColumnMapping correctly reports mapped and unmapped fields."""
    mapping = ColumnMapping({"instance_id": "uuid", "enumerator": None})
    assert mapping.is_mapped("instance_id")
    assert not mapping.is_mapped("enumerator")
    assert mapping.source_for("instance_id") == "uuid"
    assert mapping.mapped_keys() == ["instance_id"]


def test_rule_auto_registration() -> None:
    """A concrete BaseRule subclass registers itself automatically."""

    class _DummyRule(BaseRule):
        rule_id = "dummy_rule"
        name = "Dummy Rule"

        def execute(self, engine):  # type: ignore[override]
            return RuleResult(self.rule_id, self.name)

    assert "dummy_rule" in RULE_REGISTRY
    assert RULE_REGISTRY["dummy_rule"] is _DummyRule
