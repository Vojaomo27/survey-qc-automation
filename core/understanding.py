"""Dataset understanding before quality-control execution."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import pandas as pd

MAX_LINK_CANDIDATES = 100


@dataclass(frozen=True)
class ColumnProfile:
    """Observed structure and quality signals for one column."""

    name: str
    dtype: str
    role: str
    missing_percent: float
    unique_count: int
    examples: tuple[str, ...]


@dataclass(frozen=True)
class SchemaLink:
    """A likely relationship between two columns in the same dataset."""

    left: str
    right: str
    overlap_percent: float


@dataclass(frozen=True)
class DataMetric:
    """A measurable property that may affect analysis output."""

    name: str
    value: str
    impact: str


@dataclass(frozen=True)
class DataUnderstanding:
    """Summary used to guide mapping and QC decisions."""

    row_count: int
    column_count: int
    columns: tuple[ColumnProfile, ...]
    links: tuple[SchemaLink, ...]
    inconsistencies: tuple[str, ...]
    project_signals: tuple[str, ...]
    metrics: tuple[DataMetric, ...]


def _role(name: str, series: pd.Series) -> str:
    normalised = name.lower().replace("_", " ").replace("-", " ")
    if any(token in normalised.split() for token in ("id", "uuid", "key", "code")):
        return "identifier"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if series.nunique(dropna=True) <= min(20, max(3, len(series) // 20)):
        return "categorical"
    return "text"


def _links(dataframe: pd.DataFrame) -> list[SchemaLink]:
    candidates = [
        name for name in dataframe.columns
        if 1 < dataframe[name].nunique(dropna=True) <= 10000
        and not pd.api.types.is_numeric_dtype(dataframe[name])
    ]
    if len(candidates) > MAX_LINK_CANDIDATES:
        named_candidates = [
            name for name in candidates
            if any(token in str(name).lower() for token in ("id", "key", "uuid", "code"))
        ]
        candidates = (named_candidates or candidates)[:MAX_LINK_CANDIDATES]
    links: list[SchemaLink] = []
    for left, right in combinations(candidates, 2):
        left_values = set(dataframe[left].dropna().astype(str))
        right_values = set(dataframe[right].dropna().astype(str))
        if not left_values or not right_values:
            continue
        overlap = len(left_values & right_values) / min(len(left_values), len(right_values))
        if overlap >= 0.8:
            links.append(SchemaLink(str(left), str(right), round(overlap * 100, 1)))
    return links


def understand_data(dataframe: pd.DataFrame) -> DataUnderstanding:
    """Profile a dataframe without mutating it or assuming a project schema."""
    profiles: list[ColumnProfile] = []
    inconsistencies: list[str] = []
    row_count = len(dataframe.index)
    cell_count = row_count * len(dataframe.columns)
    missing_cells = int(dataframe.isna().sum().sum()) if cell_count else 0
    duplicate_rows = int(dataframe.duplicated().sum()) if row_count else 0
    high_missing_columns = 0
    constant_columns = 0
    numeric_columns = 0
    outlier_values = 0
    outlier_columns = 0
    for name in dataframe.columns:
        series = dataframe[name]
        missing_percent = round(float(series.isna().mean() * 100), 1) if row_count else 100.0
        unique_count = int(series.nunique(dropna=True))
        examples = tuple(str(value) for value in series.dropna().head(3).tolist())
        profiles.append(ColumnProfile(str(name), str(series.dtype), _role(str(name), series), missing_percent, unique_count, examples))
        if missing_percent >= 40:
            high_missing_columns += 1
            inconsistencies.append(f"{name}: {missing_percent:g}% values are missing")
        if row_count > 1 and unique_count <= 1:
            constant_columns += 1
            inconsistencies.append(f"{name}: column is constant")
        if pd.api.types.is_numeric_dtype(series):
            numeric_columns += 1
            numeric = series.dropna()
            if len(numeric) >= 4:
                lower_quartile = numeric.quantile(0.25)
                upper_quartile = numeric.quantile(0.75)
                spread = upper_quartile - lower_quartile
                if spread > 0:
                    outliers = (numeric < lower_quartile - 1.5 * spread) | (
                        numeric > upper_quartile + 1.5 * spread
                    )
                    count = int(outliers.sum())
                    if count:
                        outlier_values += count
                        outlier_columns += 1
                        inconsistencies.append(
                            f"{name}: {count} potential outlier value(s) by IQR"
                        )
    if dataframe.empty:
        inconsistencies.append("Dataset has no data rows")
    if duplicate_rows:
        inconsistencies.append(f"{duplicate_rows} complete duplicate record(s) may inflate totals")
    missing_percent = round(missing_cells / cell_count * 100, 1) if cell_count else 100.0
    metrics = (
        DataMetric("Records", f"{row_count:,}", "Determines the size of the analysis population."),
        DataMetric("Columns", f"{len(dataframe.columns):,}", "Wide files may require selective mapping and review."),
        DataMetric("Missing cells", f"{missing_percent:g}%", "Missing values can reduce usable sample size and bias summaries."),
        DataMetric("Duplicate records", f"{duplicate_rows:,}", "Duplicates can inflate counts, rates, and totals."),
        DataMetric("High-missing columns", f"{high_missing_columns:,}", "Columns with 40% or more missing values may be unreliable."),
        DataMetric("Constant columns", f"{constant_columns:,}", "Constant fields carry no analytical variation."),
        DataMetric("Numeric columns", f"{numeric_columns:,}", "Numeric fields are candidates for range and outlier checks."),
        DataMetric("Potential outlier values", f"{outlier_values:,}", "Extreme values may distort means, ranges, and model results."),
        DataMetric("Columns with outliers", f"{outlier_columns:,}", "Review these fields for valid extremes or data-entry errors."),
    )
    names = {str(name).lower().replace("_", " ") for name in dataframe.columns}
    signals: list[str] = []
    if any("household" in name or "respondent" in name for name in names):
        signals.append("household or respondent survey")
    if any("latitude" in name or "longitude" in name or "gps" in name for name in names):
        signals.append("geospatial field data")
    if any("duration" in name or "interview" in name or "enumerator" in name for name in names):
        signals.append("interview or fieldwork data")
    if not signals:
        signals.append("general structured dataset")
    return DataUnderstanding(
        row_count, len(dataframe.columns), tuple(profiles), tuple(_links(dataframe)),
        tuple(inconsistencies), tuple(signals), metrics,
    )