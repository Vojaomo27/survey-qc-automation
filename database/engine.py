"""Small in-memory data engine used by QC rules."""

from __future__ import annotations

from typing import Any

import pandas as pd


class SQLEngine:
    """Wrap the loaded worksheet and expose rule-friendly operations."""

    def __init__(self, dataframe: pd.DataFrame) -> None:
        self.dataframe = dataframe.copy()

    @property
    def row_count(self) -> int:
        return len(self.dataframe.index)

    def column(self, name: str | None) -> pd.Series:
        """Return a worksheet column, or an all-missing series if absent."""
        if not name or name not in self.dataframe.columns:
            return pd.Series(pd.NA, index=self.dataframe.index)
        return self.dataframe[name]

    def flagged_rows(self, mask: pd.Series, issue: str) -> list[dict[str, Any]]:
        """Return original records with a consistent QC issue column."""
        rows = self.dataframe.loc[mask.fillna(False)].copy()
        if rows.empty:
            return []
        rows.insert(0, "QC Issue", issue)
        rows = rows.where(pd.notna(rows), None)
        return rows.to_dict(orient="records")