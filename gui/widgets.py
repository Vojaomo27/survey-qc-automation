"""Small reusable CustomTkinter widgets.

These composites keep the page modules concise and the look consistent. They are
intentionally generic (no business logic) so any page can reuse them.
"""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from gui import theme


class InfoCard(ctk.CTkFrame):
    """A titled card showing a label and a value, used on the Dashboard.

    Attributes:
        value_label: The label widget holding the (updatable) value text.
    """

    def __init__(self, master: ctk.CTkBaseClass, title: str, value: str = "—") -> None:
        super().__init__(master, corner_radius=theme.CORNER_RADIUS, fg_color=theme.COLOR_CARD)
        ctk.CTkLabel(
            self, text=title.upper(), font=ctk.CTkFont(*theme.FONT_SMALL),
            text_color=theme.COLOR_MUTED,
        ).pack(anchor="w", padx=theme.PAD_M, pady=(theme.PAD_M, 0))
        self.value_label = ctk.CTkLabel(
            self, text=value, font=ctk.CTkFont(*theme.FONT_HEADING), anchor="w",
            justify="left", wraplength=240,
        )
        self.value_label.pack(anchor="w", padx=theme.PAD_M, pady=(0, theme.PAD_M))

    def set_value(self, value: str) -> None:
        """Update the displayed value."""
        self.value_label.configure(text=value)


class SectionTitle(ctk.CTkLabel):
    """A consistent section heading."""

    def __init__(self, master: ctk.CTkBaseClass, text: str) -> None:
        super().__init__(master, text=text, font=ctk.CTkFont(*theme.FONT_HEADING), anchor="w")


def hint_label(master: ctk.CTkBaseClass, text: str) -> ctk.CTkLabel:
    """Return a muted, small helper/hint label."""
    return ctk.CTkLabel(
        master, text=text, font=ctk.CTkFont(*theme.FONT_SMALL),
        text_color=theme.COLOR_MUTED, anchor="w", justify="left", wraplength=760,
    )
