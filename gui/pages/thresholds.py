"""Thresholds page.

Lets users view and edit every threshold that QC rules rely on — with no code
editing. Values are read from and written back to the configuration so changes
persist between sessions. Friendly labels are provided for known thresholds;
any threshold added to the config later still appears with a humanised label.
"""

from __future__ import annotations

import customtkinter as ctk

from gui import theme
from gui.pages.base_page import BasePage
from gui.widgets import hint_label

# Friendly labels for known threshold keys. Unknown keys fall back to a
# title-cased version of the key so new thresholds still render sensibly.
_LABELS: dict[str, str] = {
    "min_interview_duration": "Minimum Interview Duration (min)",
    "max_interview_duration": "Maximum Interview Duration (min)",
    "earliest_interview_time": "Earliest Interview Time (HH:MM)",
    "latest_interview_time": "Latest Interview Time (HH:MM)",
    "min_gps_accuracy": "Minimum GPS Accuracy (m)",
    "max_household_size": "Maximum Household Size",
    "min_respondent_age": "Minimum Respondent Age",
    "max_respondent_age": "Maximum Respondent Age",
    "speeding_duration": "Speeding Threshold (min)",
    "min_valid_latitude": "Minimum Valid Latitude",
    "max_valid_latitude": "Maximum Valid Latitude",
    "min_valid_longitude": "Minimum Valid Longitude",
    "max_valid_longitude": "Maximum Valid Longitude",
    "outlier_std_devs": "Outlier Detection (std deviations)",
}


class ThresholdsPage(BasePage):
    """Editable form of all QC thresholds."""

    title = "Thresholds"

    def build(self) -> None:
        """Create the entries for each threshold plus save/reset controls."""
        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, theme.PAD_S))
        ctk.CTkButton(toolbar, text="Save thresholds", command=self._save).pack(side="left")
        ctk.CTkButton(
            toolbar, text="Reset to defaults", fg_color="transparent", border_width=1,
            command=self._reset,
        ).pack(side="left", padx=theme.PAD_S)

        hint_label(
            self.body,
            "These values drive the QC checks. Edit any value and click "
            "'Save thresholds'. No coding required.",
        ).pack(fill="x", pady=(0, theme.PAD_S))

        self._scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)
        self._scroll.grid_columnconfigure(1, weight=1)
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._render()

    def on_show(self) -> None:
        """Refresh entries from config when shown."""
        if self._built:
            self._render()

    # ----------------------------------------------------------------- #
    # Rendering
    # ----------------------------------------------------------------- #
    def _render(self) -> None:
        """Draw one labelled entry per threshold."""
        for child in self._scroll.winfo_children():
            child.destroy()
        self._entries.clear()

        for row, (key, value) in enumerate(self.config.thresholds.items()):
            label = _LABELS.get(key, key.replace("_", " ").title())
            ctk.CTkLabel(self._scroll, text=label, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, theme.PAD_M), pady=5
            )
            entry = ctk.CTkEntry(self._scroll, width=160)
            entry.insert(0, str(value))
            entry.grid(row=row, column=1, sticky="w", pady=5)
            self._entries[key] = entry

    # ----------------------------------------------------------------- #
    # Actions
    # ----------------------------------------------------------------- #
    @staticmethod
    def _coerce(raw: str, previous: object) -> object:
        """Convert ``raw`` text to match the previous value's type.

        Times and other strings stay strings; numeric thresholds become int or
        float to match how they were originally stored.
        """
        raw = raw.strip()
        if isinstance(previous, bool):
            return raw.lower() in {"1", "true", "yes", "on"}
        if isinstance(previous, int) and not isinstance(previous, bool):
            try:
                return int(float(raw))
            except ValueError:
                return previous
        if isinstance(previous, float):
            try:
                return float(raw)
            except ValueError:
                return previous
        return raw

    def _save(self) -> None:
        """Write edited values back to config and persist to disk."""
        for key, entry in self._entries.items():
            self.config.set_threshold(key, self._coerce(entry.get(), self.config.get_threshold(key)))
        self.config.save()
        self.set_status("Thresholds saved.", "success")

    def _reset(self) -> None:
        """Reload the packaged default threshold values."""
        import json

        from utils.constants import DEFAULT_CONFIG_FILE

        default_thresholds = json.loads(
            DEFAULT_CONFIG_FILE.read_text(encoding="utf-8")
        )["thresholds"]
        for key, value in default_thresholds.items():
            self.config.set_threshold(key, value)
        self.config.save()
        self._render()
        self.set_status("Thresholds reset to defaults.", "info")
