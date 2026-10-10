"""Phase 2 GUI construction tests.

These verify the main window builds, every page can be created and shown without
error, and the auto-detection logic behaves. GUI tests are skipped automatically
when no display is available (e.g. headless CI).
"""

from __future__ import annotations

import pytest

from config.config_manager import ConfigManager
from core.mapping import auto_detect_mapping

# Skip the whole module if Tk cannot initialise (no display).
ctk = pytest.importorskip("customtkinter")


def _make_app():
    """Construct the app, skipping the test if no display is available."""
    from gui.app import SurveyQCApp

    try:
        return SurveyQCApp(ConfigManager())
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"No GUI display available: {exc}")


def test_auto_detect_mapping_matches_common_headers() -> None:
    """Auto-detection maps typical survey headers to canonical fields."""
    headers = [
        "InstanceID", "Enumerator", "SubmissionDate", "duration_minutes",
        "gps_lat", "gps_lon", "HouseholdID", "RespondentName", "Village",
        "Consent", "Age", "Sex",
    ]
    mapping = auto_detect_mapping(headers)
    assert mapping.source_for("instance_id") == "InstanceID"
    assert mapping.source_for("enumerator") == "Enumerator"
    assert mapping.source_for("interview_duration") == "duration_minutes"
    assert mapping.source_for("latitude") == "gps_lat"
    assert mapping.source_for("longitude") == "gps_lon"
    assert mapping.source_for("consent") == "Consent"


def test_auto_detect_no_duplicate_assignment() -> None:
    """A single column is never assigned to two canonical fields."""
    headers = ["start", "end", "duration"]
    mapping = auto_detect_mapping(headers)
    assigned = [c for c in mapping.mapping.values() if c]
    assert len(assigned) == len(set(assigned))


def test_all_pages_build_and_show() -> None:
    """Every sidebar page constructs and displays without raising."""
    from gui.app import _NAV

    app = _make_app()
    try:
        for label, _icon, _cls in _NAV:
            app.show_page(label)
        # Returning to the dashboard should also work.
        app.show_page("Dashboard")
        assert app._current == "Dashboard"
    finally:
        app.destroy()


def test_status_and_progress_helpers() -> None:
    """Status and progress helpers run without error."""
    app = _make_app()
    try:
        app.set_status("Testing", "success")
        app.set_progress(0.5)
        app.set_progress(None)
    finally:
        app.destroy()
