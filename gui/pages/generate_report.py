"""Generate Report page (scaffold).

The one-click report generation pipeline (load → SQL engine → run rules →
formatted Excel report) is assembled across Phases 4–6. This scaffold provides
the pre-run checklist and the primary action button, with generation disabled
until those phases land.
"""

from __future__ import annotations

import customtkinter as ctk

from gui import theme
from gui.pages.base_page import BasePage
from gui.widgets import hint_label


class GenerateReportPage(BasePage):
    """Pre-flight checklist and the main 'Generate Report' action."""

    title = "Generate Report"

    def build(self) -> None:
        """Create the checklist and (currently disabled) generate button."""
        hint_label(
            self.body,
            "Review the checklist, then generate a professionally formatted QC "
            "report. The generation engine is wired up in Phases 4–6.",
        ).pack(fill="x", pady=(0, theme.PAD_M))

        self._checklist = ctk.CTkFrame(self.body, corner_radius=theme.CORNER_RADIUS, fg_color=theme.COLOR_CARD)
        self._checklist.pack(fill="x")
        self._items: dict[str, ctk.CTkLabel] = {}
        for key, label in (
            ("file", "Excel file selected"),
            ("worksheet", "Worksheet loaded"),
            ("mapping", "Required fields mapped"),
            ("rules", "At least one QC rule selected"),
        ):
            row = ctk.CTkLabel(self._checklist, text=f"○  {label}", anchor="w")
            row.pack(anchor="w", padx=theme.PAD_L, pady=4)
            self._items[key] = row

        self._generate_btn = ctk.CTkButton(
            self.body, text="⚙  Generate Report", height=44,
            font=ctk.CTkFont(*theme.FONT_BODY),
            command=self.controller.generate_report,
        )
        self._generate_btn.pack(anchor="w", pady=theme.PAD_L)

    def on_show(self) -> None:
        """Update the checklist ticks from current state."""
        if self._built:
            self._refresh_checklist()

    def _refresh_checklist(self) -> None:
        """Reflect readiness of each pre-run condition."""
        state = self.state
        checks = {
            "file": bool(state.excel_path),
            "worksheet": state.has_data,
            "mapping": bool(state.mapping.mapped_keys()),
            "rules": bool(state.selected_rules),
        }
        for key, ok in checks.items():
            label = self._items[key].cget("text").lstrip("○✓ ").strip()
            mark = "✓" if ok else "○"
            colour = theme.COLOR_SUCCESS if ok else theme.COLOR_MUTED
            self._items[key].configure(text=f"{mark}  {label}", text_color=colour)
