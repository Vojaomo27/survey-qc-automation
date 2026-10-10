"""Dashboard page.

Shows an at-a-glance summary of the current session: selected file, worksheet,
record/column counts, loaded profile and output folder. It also hosts the
primary "Select Excel File" action that begins the workflow.
"""

from __future__ import annotations

import os

import customtkinter as ctk

from gui import theme
from gui.pages.base_page import BasePage
from gui.widgets import InfoCard, hint_label


class DashboardPage(BasePage):
    """Session overview and workflow entry point."""

    title = "Dashboard"

    def build(self) -> None:
        """Create the action bar and info cards."""
        action_bar = ctk.CTkFrame(self.body, fg_color="transparent")
        action_bar.pack(fill="x", pady=(0, theme.PAD_M))

        ctk.CTkButton(
            action_bar, text="📂  Select Data File", height=40,
            font=ctk.CTkFont(*theme.FONT_BODY),
            command=self.controller.select_excel_file,
        ).pack(side="left")
        ctk.CTkButton(
            action_bar, text="📄  Load Questionnaire PDF", height=40,
            command=self.controller.select_questionnaire,
        ).pack(side="left", padx=theme.PAD_S)

        hint_label(
            action_bar,
            "  Choose an Excel or SPSS file to begin. Understanding and mapping "
            "follow in the next steps.",
        ).pack(side="left", padx=theme.PAD_M)

        # Responsive grid of info cards.
        grid = ctk.CTkFrame(self.body, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="cards")

        self._cards: dict[str, InfoCard] = {}
        specs = [
            ("file", "Excel File"),
            ("worksheet", "Worksheet"),
            ("records", "Records"),
            ("columns", "Columns"),
            ("profile", "Loaded Profile"),
            ("output", "Output Folder"),
            ("understanding", "Data Understanding"),
            ("questionnaire", "Questionnaire"),
        ]
        for index, (key, title) in enumerate(specs):
            card = InfoCard(grid, title)
            card.grid(
                row=index // 3, column=index % 3, padx=theme.PAD_S,
                pady=theme.PAD_S, sticky="nsew",
            )
            self._cards[key] = card

        self.refresh()

    def on_show(self) -> None:
        """Refresh card values when the dashboard is shown."""
        if self._built:
            self.refresh()

    def refresh(self) -> None:
        """Populate the info cards from current state and configuration."""
        state = self.state
        output_folder = self.config.get_setting("output_folder") or "output/ (default)"

        self._cards["file"].set_value(
            os.path.basename(state.excel_path) if state.excel_path else "—"
        )
        self._cards["worksheet"].set_value(state.worksheet or "—")
        self._cards["records"].set_value(
            f"{state.record_count:,}" if state.record_count else "—"
        )
        self._cards["columns"].set_value(str(len(state.headers)) if state.headers else "—")
        self._cards["profile"].set_value(state.active_profile or "None")
        self._cards["output"].set_value(output_folder)
        questionnaire = os.path.basename(state.questionnaire_path) if state.questionnaire_path else "Not loaded"
        self._cards["questionnaire"].set_value(questionnaire)
        analysis = state.agent_analysis
        if analysis is None:
            self._cards["understanding"].set_value("Not analyzed")
        else:
            signals = ", ".join(analysis.understanding.project_signals)
            self._cards["understanding"].set_value(
                f"{signals} ({len(analysis.warnings)} warnings)"
            )
