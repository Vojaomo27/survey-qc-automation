"""Default survey checks shipped with the application."""

from __future__ import annotations

import pandas as pd

from core.models import RuleResult
from rules.base_rule import BaseRule


def _result(rule: BaseRule, rows: list[dict]) -> RuleResult:
    return RuleResult(
        rule.rule_id,
        rule.name,
        len(rows),
        list(rows[0]) if rows else [],
        rows,
        severity=rule.severity,
    )


class RequiredFieldsRule(BaseRule):
    rule_id = "required_fields"
    name = "Required fields are populated"
    description = "Flags records missing an instance ID or enumerator."
    category = "Completeness"
    required_fields = ("instance_id", "enumerator")
    severity = "high"

    def execute(self, engine):  # type: ignore[override]
        mask = engine.column(self.col("instance_id")).isna() | engine.column(
            self.col("enumerator")
        ).isna()
        return _result(self, engine.flagged_rows(mask, "Missing required field"))


class DuplicateInstanceRule(BaseRule):
    rule_id = "duplicate_instance_id"
    name = "Duplicate instance IDs"
    description = "Flags repeated submission identifiers."
    category = "Completeness"
    required_fields = ("instance_id",)
    severity = "high"

    def execute(self, engine):  # type: ignore[override]
        values = engine.column(self.col("instance_id"))
        mask = values.notna() & values.astype(str).duplicated(keep=False)
        return _result(self, engine.flagged_rows(mask, "Duplicate instance ID"))


class InterviewDurationRule(BaseRule):
    rule_id = "interview_duration"
    name = "Interview duration within limits"
    description = "Flags interviews outside the configured duration limits."
    category = "Timing"
    required_fields = ("interview_duration",)

    def execute(self, engine):  # type: ignore[override]
        values = pd.to_numeric(engine.column(self.col("interview_duration")), errors="coerce")
        minimum = float(self.thresholds.get("min_interview_duration", 0))
        maximum = float(self.thresholds.get("max_interview_duration", float("inf")))
        mask = values.notna() & ((values < minimum) | (values > maximum))
        return _result(self, engine.flagged_rows(mask, f"Duration outside {minimum:g}-{maximum:g} minutes"))


class GpsBoundsRule(BaseRule):
    rule_id = "gps_bounds"
    name = "GPS coordinates are valid"
    description = "Flags coordinates outside valid latitude and longitude ranges."
    category = "GPS"
    required_fields = ("latitude", "longitude")

    def execute(self, engine):  # type: ignore[override]
        latitude = pd.to_numeric(engine.column(self.col("latitude")), errors="coerce")
        longitude = pd.to_numeric(engine.column(self.col("longitude")), errors="coerce")
        mask = latitude.notna() & longitude.notna() & (
            (latitude < float(self.thresholds.get("min_valid_latitude", -90)))
            | (latitude > float(self.thresholds.get("max_valid_latitude", 90)))
            | (longitude < float(self.thresholds.get("min_valid_longitude", -180)))
            | (longitude > float(self.thresholds.get("max_valid_longitude", 180)))
        )
        return _result(self, engine.flagged_rows(mask, "GPS coordinate outside valid bounds"))


class RespondentAgeRule(BaseRule):
    rule_id = "respondent_age"
    name = "Respondent age within limits"
    description = "Flags ages outside the configured limits."
    category = "Demographics"
    required_fields = ("age",)

    def execute(self, engine):  # type: ignore[override]
        values = pd.to_numeric(engine.column(self.col("age")), errors="coerce")
        minimum = float(self.thresholds.get("min_respondent_age", 0))
        maximum = float(self.thresholds.get("max_respondent_age", 150))
        mask = values.notna() & ((values < minimum) | (values > maximum))
        return _result(self, engine.flagged_rows(mask, f"Age outside {minimum:g}-{maximum:g} years"))


class NumericOutlierRule(BaseRule):
    rule_id = "numeric_outliers"
    name = "Potential numeric outliers"
    description = "Flags records containing values outside the 1.5 IQR range."
    category = "Distribution"
    severity = "medium"

    def execute(self, engine):  # type: ignore[override]
        mask = pd.Series(False, index=engine.dataframe.index)
        outlier_columns: list[str] = []
        for column in engine.dataframe.select_dtypes(include="number").columns:
            values = engine.dataframe[column]
            lower_quartile = values.quantile(0.25)
            upper_quartile = values.quantile(0.75)
            spread = upper_quartile - lower_quartile
            if pd.notna(spread) and spread > 0:
                column_mask = (values < lower_quartile - 1.5 * spread) | (
                    values > upper_quartile + 1.5 * spread
                )
                if column_mask.any():
                    mask |= column_mask.fillna(False)
                    outlier_columns.append(str(column))
        issue = "Potential outlier in: " + ", ".join(outlier_columns)
        return _result(self, engine.flagged_rows(mask, issue))