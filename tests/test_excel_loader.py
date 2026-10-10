"""Tests for resilient worksheet loading and header detection."""

from __future__ import annotations

import pandas as pd
import pytest

pyreadstat = pytest.importorskip("pyreadstat")

from core.excel_loader import load_worksheet
from core.mapping import auto_detect_mapping
from core.understanding import understand_data


def test_loader_finds_header_after_title_and_unique_names(tmp_path) -> None:
    """Decorative title rows and duplicate headers do not break loading."""
    path = tmp_path / "export.xlsx"
    pd.DataFrame(
        [
            ["Project export", None, None],
            ["Instance ID", "Age", "Age"],
            ["a-1", 24, 25],
        ]
    ).to_excel(path, index=False, header=False)

    loaded = load_worksheet(path, "Sheet1")

    assert loaded.header_row == 1
    assert list(loaded.dataframe.columns) == ["Instance ID", "Age", "Age.1"]
    assert len(loaded.dataframe.index) == 1


def test_mapping_accepts_minor_header_variations() -> None:
    """Small spelling differences still produce useful suggestions."""
    mapping = auto_detect_mapping(["InstanceID", "enumeratr", "GPS Latitude"])

    assert mapping.source_for("instance_id") == "InstanceID"
    assert mapping.source_for("enumerator") == "enumeratr"
    assert mapping.source_for("latitude") == "GPS Latitude"


def test_loader_reads_spss_sav(tmp_path) -> None:
    """SPSS files enter the same cleaned dataframe workflow as Excel files."""
    path = tmp_path / "survey.sav"
    pyreadstat.write_sav(pd.DataFrame({"household_id": ["h1", "h2"], "latitude": [1.0, 2.0]}), path)

    loaded = load_worksheet(path, "Data")
    understanding = understand_data(loaded.dataframe)

    assert loaded.header_row == -1
    assert loaded.dataframe.shape == (2, 2)
    assert "household or respondent survey" in understanding.project_signals
    assert "geospatial field data" in understanding.project_signals


def test_loader_reads_csv_with_title_and_semicolon_delimiter(tmp_path) -> None:
    """CSV files with a decorative title and semicolon delimiter are supported."""
    path = tmp_path / "survey.csv"
    path.write_text(
        "Survey export;;;\nInstance ID;Enumerator;Age;Age\na-1;A;24;25\n",
        encoding="utf-8",
    )

    loaded = load_worksheet(path, "Data")

    assert loaded.header_row == 1
    assert list(loaded.dataframe.columns) == ["Instance ID", "Enumerator", "Age", "Age.1"]
    assert loaded.dataframe.iloc[0]["Instance ID"] == "a-1"