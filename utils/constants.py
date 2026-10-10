"""Application-wide constants and filesystem paths.

This module centralises every hard-coded value used across the application so
that nothing is scattered through the codebase. Paths are resolved relative to
the project root, which keeps the app portable and PyInstaller-compatible.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

# --------------------------------------------------------------------------- #
# Application metadata
# --------------------------------------------------------------------------- #
APP_NAME: Final[str] = "Survey QC Automation Tool"
APP_SHORT_NAME: Final[str] = "SurveyQC"
APP_VERSION: Final[str] = "1.0.0"
APP_AUTHOR: Final[str] = "Survey QC Team"


def get_base_dir() -> Path:
    """Return the application base directory.

    When the app is frozen by PyInstaller the code runs from a temporary
    extraction directory (``sys._MEIPASS``); user-facing folders such as
    ``logs`` and ``output`` must instead live next to the executable. When
    running from source we use the project root (the parent of ``utils``).

    Returns:
        Path to the directory that should host runtime folders.
    """
    if getattr(sys, "frozen", False):
        # Running inside a PyInstaller bundle: use the executable's folder.
        return Path(sys.executable).resolve().parent
    # Running from source: project root is one level above this file's folder.
    return Path(__file__).resolve().parent.parent


BASE_DIR: Final[Path] = get_base_dir()
RESOURCE_DIR: Final[Path] = (
    Path(getattr(sys, "_MEIPASS")) if getattr(sys, "frozen", False) else BASE_DIR
)

# --------------------------------------------------------------------------- #
# Runtime directories
# --------------------------------------------------------------------------- #
CONFIG_DIR: Final[Path] = BASE_DIR / "config"
ASSETS_DIR: Final[Path] = BASE_DIR / "assets"
LOGS_DIR: Final[Path] = BASE_DIR / "logs"
INPUT_DIR: Final[Path] = BASE_DIR / "input"
OUTPUT_DIR: Final[Path] = BASE_DIR / "output"
PROFILES_DIR: Final[Path] = CONFIG_DIR / "profiles"

# --------------------------------------------------------------------------- #
# Configuration files
# --------------------------------------------------------------------------- #
DEFAULT_CONFIG_FILE: Final[Path] = RESOURCE_DIR / "config" / "default_config.json"
USER_CONFIG_FILE: Final[Path] = CONFIG_DIR / "user_config.json"
LLM_API_KEY_FILE: Final[Path] = CONFIG_DIR / "llm_api_key.txt"

# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
# The Excel data is loaded into a single in-memory SQLite table with this name.
SURVEY_TABLE_NAME: Final[str] = "survey"

# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
DEFAULT_REPORT_PREFIX: Final[str] = "QC_Report"
REPORT_SHEET_NAME: Final[str] = "QC Report"

# --------------------------------------------------------------------------- #
# GUI appearance
# --------------------------------------------------------------------------- #
APPEARANCE_MODES: Final[tuple[str, ...]] = ("System", "Light", "Dark")
COLOR_THEMES: Final[tuple[str, ...]] = ("blue", "green", "dark-blue")
DEFAULT_WINDOW_SIZE: Final[tuple[int, int]] = (1200, 760)
MIN_WINDOW_SIZE: Final[tuple[int, int]] = (960, 600)


def ensure_runtime_dirs() -> None:
    """Create all runtime directories if they do not yet exist.

    Called once at start-up so that logging, profile storage and report output
    never fail because a folder is missing.
    """
    for directory in (LOGS_DIR, INPUT_DIR, OUTPUT_DIR, CONFIG_DIR, PROFILES_DIR):
        directory.mkdir(parents=True, exist_ok=True)
