"""Core domain models shared across the application.

These lightweight, typed data structures are the common vocabulary used by the
GUI, the database engine, the rule engine and the report generator. Keeping
them free of behaviour (beyond simple helpers) avoids coupling between layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FieldType(str, Enum):
    """Logical data type of a canonical survey field."""

    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    BOOLEAN = "boolean"


@dataclass(frozen=True)
class CanonicalField:
    """A survey field the application understands independent of its column name.

    QC rules refer to canonical field keys (e.g. ``instance_id``) rather than to
    the raw spreadsheet header, so a rule works regardless of how a given survey
    labelled its columns. The column mapping connects the two.

    Attributes:
        key: Stable identifier used by rules and mappings.
        label: Human-friendly name shown in the GUI.
        field_type: Expected logical type, used for validation/casting.
        aliases: Lower-case header fragments used for automatic detection.
        required: Whether the field is generally expected in a survey dataset.
    """

    key: str
    label: str
    field_type: FieldType = FieldType.TEXT
    aliases: tuple[str, ...] = ()
    required: bool = False


@dataclass
class ColumnMapping:
    """Mapping from canonical field keys to actual spreadsheet column names.

    Attributes:
        mapping: ``{canonical_key: source_column_name}``. A key absent from the
            dict (or mapped to ``None``) is considered unmapped.
    """

    mapping: dict[str, Optional[str]] = field(default_factory=dict)

    def source_for(self, key: str) -> Optional[str]:
        """Return the source column mapped to ``key`` or ``None`` if unmapped."""
        value = self.mapping.get(key)
        return value or None

    def is_mapped(self, key: str) -> bool:
        """Return ``True`` if ``key`` is mapped to a non-empty column name."""
        return bool(self.source_for(key))

    def mapped_keys(self) -> list[str]:
        """Return the list of canonical keys that have a source column."""
        return [k for k in self.mapping if self.is_mapped(k)]


@dataclass
class RuleResult:
    """Outcome of running a single QC rule.

    Attributes:
        rule_id: Stable identifier of the rule that produced this result.
        title: Human-readable section title for the report.
        flagged_count: Number of records that failed the check.
        columns: Ordered column names for the flagged-records table.
        rows: Flagged records as a list of row dictionaries.
        skipped: ``True`` if the rule could not run (e.g. missing mapping).
        message: Optional explanatory note (why skipped, extra detail, etc.).
        severity: Relative importance, used for report ordering/emphasis.
    """

    rule_id: str
    title: str
    flagged_count: int = 0
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    skipped: bool = False
    message: str = ""
    severity: str = "medium"

    @property
    def has_flags(self) -> bool:
        """Return ``True`` if this rule flagged at least one record."""
        return self.flagged_count > 0
