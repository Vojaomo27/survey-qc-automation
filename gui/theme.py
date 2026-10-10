"""Shared visual constants for the GUI.

Centralising colours, fonts and spacing keeps the interface consistent and makes
restyling a one-file change. Colours are given as ``(light, dark)`` tuples so
CustomTkinter picks the correct one for the active appearance mode.
"""

from __future__ import annotations

from typing import Final

# Brand / accent colours (light, dark).
COLOR_PRIMARY: Final[tuple[str, str]] = ("#1f4e79", "#2b5f8f")
COLOR_PRIMARY_HOVER: Final[tuple[str, str]] = ("#163a5a", "#3a72a6")
COLOR_SIDEBAR: Final[tuple[str, str]] = ("#e8edf2", "#1a1a1a")
COLOR_CARD: Final[tuple[str, str]] = ("#ffffff", "#2b2b2b")
COLOR_SUCCESS: Final[tuple[str, str]] = ("#2e7d32", "#43a047")
COLOR_WARNING: Final[tuple[str, str]] = ("#c77700", "#ff9800")
COLOR_ERROR: Final[tuple[str, str]] = ("#c62828", "#ef5350")
COLOR_MUTED: Final[tuple[str, str]] = ("#5a6673", "#9aa4ad")

# Report palette (hex strings used by OpenPyXL in Phase 6).
REPORT_HEADER_FILL: Final[str] = "1F4E79"
REPORT_HEADER_FONT: Final[str] = "FFFFFF"
REPORT_ALT_ROW_FILL: Final[str] = "DCE6F1"

# Typography.
FONT_FAMILY: Final[str] = "Segoe UI"
FONT_TITLE: Final[tuple[str, int, str]] = (FONT_FAMILY, 22, "bold")
FONT_HEADING: Final[tuple[str, int, str]] = (FONT_FAMILY, 16, "bold")
FONT_BODY: Final[tuple[str, int]] = (FONT_FAMILY, 13)
FONT_SMALL: Final[tuple[str, int]] = (FONT_FAMILY, 11)

# Spacing.
PAD_S: Final[int] = 6
PAD_M: Final[int] = 12
PAD_L: Final[int] = 20
CORNER_RADIUS: Final[int] = 8
