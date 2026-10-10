"""About page — static application information."""

from __future__ import annotations

import customtkinter as ctk

from gui import theme
from gui.pages.base_page import BasePage
from utils.constants import APP_AUTHOR, APP_NAME, APP_VERSION


class AboutPage(BasePage):
    """Displays application metadata and a short description."""

    title = "About"

    def build(self) -> None:
        """Render static app information."""
        card = ctk.CTkFrame(self.body, corner_radius=theme.CORNER_RADIUS, fg_color=theme.COLOR_CARD)
        card.pack(fill="x")

        ctk.CTkLabel(card, text=APP_NAME, font=ctk.CTkFont(*theme.FONT_HEADING)).pack(
            anchor="w", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_S)
        )
        info = (
            f"Version {APP_VERSION}\n"
            f"Author: {APP_AUTHOR}\n\n"
            "Automates quality-control checks on survey datasets stored in "
            "Microsoft Excel files. Select a file, map columns, choose checks, "
            "and generate a professionally formatted QC report — no coding "
            "required."
        )
        ctk.CTkLabel(card, text=info, justify="left", anchor="w", wraplength=680).pack(
            anchor="w", padx=theme.PAD_L, pady=(0, theme.PAD_L)
        )
