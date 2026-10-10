"""Abstract base class and registry for QC rules.

Every quality-control check is an independent subclass of :class:`BaseRule`.
Rules register themselves automatically via ``__init_subclass__`` so that new
checks become available to the GUI and engine simply by defining a class in the
``rules`` package — no central list to edit. This satisfies the requirement that
the architecture support *unlimited* new QC rules.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, ClassVar

from core.models import ColumnMapping, RuleResult
from utils.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from database.engine import SQLEngine

logger = get_logger(__name__)

# Global registry mapping rule_id -> rule class. Populated automatically.
RULE_REGISTRY: dict[str, type["BaseRule"]] = {}


class BaseRule(abc.ABC):
    """Base class for all QC rules.

    Subclasses declare metadata as class attributes and implement
    :meth:`execute`. The engine constructs a subclass with the active thresholds
    and column mapping, checks :meth:`can_run`, then calls :meth:`run`.

    Class attributes:
        rule_id: Unique, stable identifier (snake_case). Used as registry key.
        name: Human-readable rule name shown in the GUI and report.
        description: Short explanation of what the rule flags.
        category: Grouping label (e.g. ``"Timing"``, ``"GPS"``).
        required_fields: Canonical field keys that must be mapped to run.
        default_enabled: Whether the rule is ticked by default.
        severity: Default severity for produced results.
    """

    rule_id: ClassVar[str] = ""
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    category: ClassVar[str] = "General"
    required_fields: ClassVar[tuple[str, ...]] = ()
    default_enabled: ClassVar[bool] = True
    severity: ClassVar[str] = "medium"

    def __init__(self, mapping: ColumnMapping, thresholds: dict[str, Any]) -> None:
        """Store the active mapping and thresholds for this run.

        Args:
            mapping: Column mapping connecting canonical keys to columns.
            thresholds: Flattened threshold values keyed by threshold name.
        """
        self.mapping = mapping
        self.thresholds = thresholds

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-register concrete rule subclasses in :data:`RULE_REGISTRY`."""
        super().__init_subclass__(**kwargs)
        # Only register concrete, non-abstract rules with a declared id.
        if getattr(cls, "rule_id", "") and not getattr(cls, "__abstractmethods__", None):
            if cls.rule_id in RULE_REGISTRY:
                logger.warning("Duplicate rule_id '%s' overrides previous rule.", cls.rule_id)
            RULE_REGISTRY[cls.rule_id] = cls

    # ----------------------------------------------------------------- #
    # Overridable behaviour
    # ----------------------------------------------------------------- #
    def can_run(self) -> tuple[bool, str]:
        """Return whether the rule has everything it needs to execute.

        The default implementation checks that all ``required_fields`` are
        mapped. Subclasses may override for more nuanced requirements.

        Returns:
            Tuple ``(ok, reason)`` where ``reason`` explains a ``False`` result.
        """
        missing = [k for k in self.required_fields if not self.mapping.is_mapped(k)]
        if missing:
            return False, f"Unmapped required field(s): {', '.join(missing)}"
        return True, ""

    @abc.abstractmethod
    def execute(self, engine: "SQLEngine") -> RuleResult:
        """Run the check and return its result.

        Args:
            engine: The SQL engine wrapping the loaded survey data.

        Returns:
            A populated :class:`RuleResult`.
        """
        raise NotImplementedError

    # ----------------------------------------------------------------- #
    # Engine entry point
    # ----------------------------------------------------------------- #
    def run(self, engine: "SQLEngine") -> RuleResult:
        """Guarded wrapper around :meth:`execute`.

        Skips gracefully when prerequisites are missing and converts unexpected
        errors into a skipped result so a single failing rule never aborts the
        whole QC run.

        Args:
            engine: The SQL engine wrapping the loaded survey data.

        Returns:
            A :class:`RuleResult`; ``skipped`` is ``True`` on missing data/errors.
        """
        ok, reason = self.can_run()
        if not ok:
            logger.info("Rule '%s' skipped: %s", self.rule_id, reason)
            return RuleResult(self.rule_id, self.name, skipped=True, message=reason)
        try:
            result = self.execute(engine)
            logger.info("Rule '%s' flagged %d record(s).", self.rule_id, result.flagged_count)
            return result
        except Exception as exc:  # noqa: BLE001 - defensive: isolate rule failures
            logger.exception("Rule '%s' failed to execute.", self.rule_id)
            return RuleResult(
                self.rule_id, self.name, skipped=True,
                message=f"Execution error: {exc}",
            )

    # ----------------------------------------------------------------- #
    # Helpers for subclasses
    # ----------------------------------------------------------------- #
    def col(self, key: str) -> str | None:
        """Return the source column mapped to canonical ``key`` (or ``None``)."""
        return self.mapping.source_for(key)
