"""Application-level agent for recommending and running QC checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.models import ColumnMapping, RuleResult
from core.understanding import DataUnderstanding, understand_data
from database import SQLEngine
from rules.base_rule import RULE_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class AgentAnalysis:
    """Advice produced before a QC run."""

    recommended_rules: tuple[str, ...]
    warnings: tuple[str, ...]
    understanding: DataUnderstanding
    dataframe: pd.DataFrame


class QCAgent:
    """Coordinate mapping-aware rule selection and execution."""

    def analyze(self, dataframe: pd.DataFrame, mapping: ColumnMapping) -> AgentAnalysis:
        """Recommend runnable default checks and report missing prerequisites."""
        logger.info(
            "[Understanding 1/3] Profiling %d rows and %d columns...",
            len(dataframe.index), len(dataframe.columns),
        )
        understanding = understand_data(dataframe)
        logger.info(
            "[Understanding 2/3] Detected signals: %s",
            ", ".join(understanding.project_signals),
        )
        recommended: list[str] = []
        warnings: list[str] = []
        for rule_id, rule_class in RULE_REGISTRY.items():
            rule = rule_class(mapping, {})
            ok, reason = rule.can_run()
            if rule.default_enabled and ok:
                recommended.append(rule_id)
            elif not ok:
                warnings.append(f"{rule.name}: {reason}")
        warnings.extend(understanding.inconsistencies)
        logger.info(
            "[Understanding 3/3] Analysis complete: %d recommended rules, %d warnings, %d candidate links.",
            len(recommended), len(warnings), len(understanding.links),
        )
        return AgentAnalysis(tuple(recommended), tuple(warnings), understanding, dataframe)

    def run(
        self,
        dataframe: pd.DataFrame,
        mapping: ColumnMapping,
        thresholds: dict[str, Any],
        selected_rules: set[str] | None = None,
    ) -> list[RuleResult]:
        """Run selected registered rules and return isolated results."""
        engine = SQLEngine(dataframe)
        rule_ids = selected_rules or {
            rule_id for rule_id, rule_class in RULE_REGISTRY.items() if rule_class.default_enabled
        }
        results: list[RuleResult] = []
        logger.info("[QC 1/3] Running %d selected rule(s)...", len(rule_ids))
        for index, rule_id in enumerate(rule_ids, start=1):
            rule_class = RULE_REGISTRY.get(rule_id)
            if rule_class is not None:
                logger.info("[QC 2/3] Rule %d/%d: %s", index, len(rule_ids), rule_class.name)
                result = rule_class(mapping, thresholds).run(engine)
                results.append(result)
                logger.info(
                    "[QC 2/3] Result: %d flagged%s.",
                    result.flagged_count,
                    " (skipped: %s)" % result.message if result.skipped else "",
                )
        logger.info("[QC 3/3] Rule execution complete.")
        return results