"""Profiles page (scaffold).

Reusable survey templates — each storing column mappings, thresholds, selected
QC checks and output preferences — are implemented in Phase 7. This scaffold
establishes the page and its place in the workflow; the toolbar actions are
wired to placeholders until then.
"""

from __future__ import annotations

import customtkinter as ctk

from gui import theme
from gui.pages.base_page import BasePage
from gui.widgets import hint_label


class ProfilesPage(BasePage):
    """Manage reusable survey profiles (full behaviour in Phase 7)."""

    title = "Profiles"

    def build(self) -> None:
        """Create the profile toolbar and list placeholder."""
        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, theme.PAD_S))
        for label in ("Save", "Edit", "Delete", "Duplicate", "Import", "Export"):
            ctk.CTkButton(
                toolbar, text=label, width=90, state="disabled",
            ).pack(side="left", padx=(0, theme.PAD_S))

        hint_label(
            self.body,
            "Profiles store column mappings, thresholds, selected checks and "
            "output preferences for each survey template (Baseline, Endline, "
            "Household, etc.). Full profile management arrives in Phase 7.",
        ).pack(fill="x", pady=(0, theme.PAD_M))

        placeholder = ctk.CTkFrame(self.body, corner_radius=theme.CORNER_RADIUS, fg_color=theme.COLOR_CARD)
        placeholder.pack(fill="both", expand=True)
        ctk.CTkLabel(
            placeholder, text="No profiles yet.", text_color=theme.COLOR_MUTED,
        ).pack(pady=theme.PAD_L)
