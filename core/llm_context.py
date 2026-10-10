"""Build compact, privacy-aware context for an LLM data-understanding pass."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from core.agent import AgentAnalysis

MAX_CONTEXT_CHARS = 120_000
MAX_COLUMNS = 3_000
MAX_ROW_SESSIONS = 20
MAX_VALUES_PER_COLUMN = 8
MAX_SESSION_COLUMNS = 80
MAX_EVIDENCE_ROWS = 25
MAX_EVIDENCE_COLUMNS = 30


def _safe_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _question_profile(dataframe: pd.DataFrame, column: str) -> dict[str, Any]:
    series = dataframe[column]
    non_null = series.dropna()
    profile: dict[str, Any] = {
        "column": str(column),
        "dtype": str(series.dtype),
        "question_like_name": str(column),
        "missing_percent": round(float(series.isna().mean() * 100), 1),
        "unique_count": int(series.nunique(dropna=True)),
        "examples": [_safe_value(value) for value in non_null.head(3)],
    }
    if profile["unique_count"] <= 30:
        counts = non_null.astype(str).value_counts().head(MAX_VALUES_PER_COLUMN)
        profile["response_distribution"] = {
            str(key): int(value) for key, value in counts.items()
        }
    elif pd.api.types.is_numeric_dtype(series):
        profile["numeric_summary"] = {
            "min": _safe_value(non_null.min()) if not non_null.empty else None,
            "median": _safe_value(non_null.median()) if not non_null.empty else None,
            "max": _safe_value(non_null.max()) if not non_null.empty else None,
        }
    return profile


def build_study_context(
    dataframe: pd.DataFrame,
    analysis: AgentAnalysis,
    questionnaire_text: str = "",
) -> dict[str, Any]:
    """Create a bounded schema/question/response/session narrative.

    Raw values are sampled only for a small number of sessions. The complete
    dataset is never serialized into the LLM request.
    """
    columns = [str(column) for column in dataframe.columns[:MAX_COLUMNS]]
    identifier = next(
        (
            column for column in columns
            if any(token in column.lower() for token in ("instance", "uuid", "case", "record", "key", "id"))
        ),
        None,
    )
    row_sessions: list[dict[str, Any]] = []
    selected = dataframe.head(MAX_ROW_SESSIONS)
    session_columns = columns[:MAX_SESSION_COLUMNS]
    for index, row in selected.iterrows():
        values = {column: _safe_value(row[column]) for column in session_columns}
        row_sessions.append({"row_number": int(index) + 1, "instance_id": values.get(identifier) if identifier else None, "responses": values})

    context = {
        "purpose": "Understand the study, questionnaire structure, response patterns, and data-management risks before QC.",
        "questionnaire_text": questionnaire_text[:30_000],
        "dataset": {
            "records": len(dataframe.index),
            "columns": len(dataframe.columns),
            "project_signals": list(analysis.understanding.project_signals),
            "metrics": [metric.__dict__ for metric in analysis.understanding.metrics],
            "issues": list(analysis.understanding.inconsistencies[:200]),
            "candidate_links": [link.__dict__ for link in analysis.understanding.links[:100]],
        },
        "questions": [_question_profile(dataframe, column) for column in columns],
        "row_sessions": row_sessions,
        "instructions": [
            "Infer likely study purpose and units of analysis, but label uncertainty.",
            "Treat each column as a possible questionnaire question and explain likely meaning from its name and responses.",
            "Look for skip-pattern contradictions, impossible combinations, repeated sessions, and broken entity links.",
            "Return proposed checks with evidence and confidence; do not modify data.",
        ],
    }
    serialized = json.dumps(context, default=str)
    if len(serialized) <= MAX_CONTEXT_CHARS:
        return context
    context["row_sessions"] = context["row_sessions"][:5]
    context["questionnaire_text"] = context["questionnaire_text"][:10_000]
    for question in context["questions"]:
        question.pop("examples", None)
        question.pop("response_distribution", None)
    return context


def build_chat_evidence(dataframe: pd.DataFrame, message: str) -> dict[str, Any]:
    """Retrieve small, relevant evidence from the full dataframe for one chat question."""
    query = message.lower()
    evidence: dict[str, Any] = {"question": message, "matched_rows": [], "relevant_columns": []}
    columns = [str(column) for column in dataframe.columns]
    mentioned_columns = [column for column in columns if column.lower() in query]
    evidence["relevant_columns"] = mentioned_columns[:MAX_EVIDENCE_COLUMNS]

    identifier_columns = [
        column for column in columns
        if any(token in column.lower() for token in ("instance", "uuid", "case", "record", "key", "id"))
    ]
    for column in identifier_columns[:5]:
        values = dataframe[column].dropna().astype(str)
        matches = values[values.str.lower().isin(query.split())]
        if matches.empty:
            matches = values[values.str.lower().apply(lambda value: value in query)]
        if not matches.empty:
            rows = dataframe.loc[matches.index].head(MAX_EVIDENCE_ROWS)
            evidence["matched_rows"] = rows.iloc[:, :MAX_EVIDENCE_COLUMNS].where(
                pd.notna(rows.iloc[:, :MAX_EVIDENCE_COLUMNS]), None
            ).to_dict(orient="records")
            evidence["matched_by"] = column
            break

    if any(token in query for token in ("missing", "blank", "null", "empty")):
        missing = dataframe.isna().mean().sort_values(ascending=False).head(MAX_EVIDENCE_COLUMNS)
        evidence["missingness"] = {str(column): round(float(value * 100), 1) for column, value in missing.items()}
    if any(token in query for token in ("duplicate", "duplicated")):
        duplicate_mask = dataframe.duplicated(keep=False)
        for column in identifier_columns[:5]:
            duplicate_mask |= dataframe[column].notna() & dataframe[column].duplicated(keep=False)
        duplicates = dataframe[duplicate_mask].head(MAX_EVIDENCE_ROWS)
        evidence["duplicate_rows"] = duplicates.iloc[:, :MAX_EVIDENCE_COLUMNS].where(
            pd.notna(duplicates.iloc[:, :MAX_EVIDENCE_COLUMNS]), None
        ).to_dict(orient="records")
    if any(token in query for token in ("outlier", "extreme", "unusual")):
        outlier_columns: dict[str, list[Any]] = {}
        for column in dataframe.select_dtypes(include="number").columns[:MAX_EVIDENCE_COLUMNS]:
            values = dataframe[column]
            lower = values.quantile(0.25)
            upper = values.quantile(0.75)
            spread = upper - lower
            if pd.notna(spread) and spread > 0:
                mask = (values < lower - 1.5 * spread) | (values > upper + 1.5 * spread)
                if mask.any():
                    outlier_columns[str(column)] = [
                        _safe_value(value) for value in values[mask].head(MAX_EVIDENCE_ROWS)
                    ]
        evidence["outliers"] = outlier_columns
    return evidence