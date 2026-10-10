"""Flexible Excel worksheet loading for varied project workbooks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyreadstat

from core.canonical_fields import CANONICAL_FIELDS


@dataclass(frozen=True)
class LoadedWorksheet:
    """A cleaned worksheet and the row used as its header."""

    dataframe: pd.DataFrame
    header_row: int


def _normalise(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _header_score(row: pd.Series) -> tuple[int, int]:
    values = [value for value in row.tolist() if pd.notna(value) and str(value).strip()]
    aliases = {_normalise(alias) for field in CANONICAL_FIELDS for alias in field.aliases}
    known = sum(1 for value in values if _normalise(value) in aliases)
    return known, len(values)


def _unique_headers(values: list[object]) -> list[str]:
    """Convert arbitrary Excel headers into stable, non-empty column names."""
    names: list[str] = []
    counts: dict[str, int] = {}
    for index, value in enumerate(values, start=1):
        base = str(value).strip() if pd.notna(value) else ""
        base = base or f"Column_{index}"
        counts[base] = counts.get(base, 0) + 1
        names.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    return names


def _read_csv(path: str | Path, header: int | None, nrows: int | None = None) -> pd.DataFrame:
    """Read common CSV variants, including semicolon and tab delimiters."""
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return pd.read_csv(
                path,
                header=header,
                nrows=nrows,
                sep=None,
                engine="python",
                encoding=encoding,
                on_bad_lines="warn",
            )
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            last_error = exc
    raise ValueError(f"Could not parse CSV file: {last_error}") from last_error


def _clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe.columns = _unique_headers(list(dataframe.columns))
    dataframe = dataframe.dropna(axis=0, how="all").dropna(axis=1, how="all")
    return dataframe.reset_index(drop=True)


def load_worksheet(path: str | Path, sheet_name: str) -> LoadedWorksheet:
    """Load a worksheet even when titles or blank rows precede its headers."""
    suffix = Path(path).suffix.lower()
    if suffix == ".sav":
        dataframe, _metadata = pyreadstat.read_sav(path)
        return LoadedWorksheet(_clean_dataframe(dataframe), -1)

    if suffix == ".csv":
        preview = _read_csv(path, header=None, nrows=50)
        if preview.empty:
            return LoadedWorksheet(pd.DataFrame(), 0)
        scores = [_header_score(preview.iloc[index]) for index in range(len(preview.index))]
        known_max = max(score[0] for score in scores)
        if known_max:
            candidates = [index for index, score in enumerate(scores) if score[0] == known_max]
        else:
            populated_max = max(score[1] for score in scores)
            candidates = [index for index, score in enumerate(scores) if score[1] == populated_max]
        header_row = candidates[0]
        return LoadedWorksheet(_clean_dataframe(_read_csv(path, header=header_row)), header_row)

    preview = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=50)
    if preview.empty:
        return LoadedWorksheet(pd.DataFrame(), 0)

    scores = [_header_score(preview.iloc[index]) for index in range(len(preview.index))]
    known_max = max(score[0] for score in scores)
    if known_max:
        candidates = [index for index, score in enumerate(scores) if score[0] == known_max]
    else:
        populated_max = max(score[1] for score in scores)
        candidates = [index for index, score in enumerate(scores) if score[1] == populated_max]
    header_row = candidates[0]

    dataframe = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    return LoadedWorksheet(_clean_dataframe(dataframe), header_row)