"""Reusable modal dialogs."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from gui import theme


class WorksheetDialog(ctk.CTkToplevel):
    """Modal dialog prompting the user to pick a worksheet from a workbook.

    Attributes:
        selection: The chosen worksheet name, or ``None`` if cancelled.
    """

    def __init__(self, master: ctk.CTkBaseClass, sheet_names: list[str]) -> None:
        super().__init__(master)
        self.title("Select Worksheet")
        self.geometry("360x180")
        self.resizable(False, False)
        self.selection: Optional[str] = None

        ctk.CTkLabel(self, text="Choose a worksheet to load:").pack(
            anchor="w", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_S)
        )
        self._menu = ctk.CTkOptionMenu(self, values=sheet_names or ["(none)"])
        self._menu.set(sheet_names[0] if sheet_names else "(none)")
        self._menu.pack(fill="x", padx=theme.PAD_L)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=theme.PAD_L, pady=theme.PAD_L)
        ctk.CTkButton(buttons, text="Cancel", fg_color="transparent", border_width=1,
                      command=self._cancel).pack(side="right", padx=(theme.PAD_S, 0))
        ctk.CTkButton(buttons, text="Load", command=self._confirm).pack(side="right")

        # Make the dialog modal relative to its parent.
        self.transient(master)  # type: ignore[arg-type]
        self.grab_set()
        self.after(50, self._center_on_parent)

    def _center_on_parent(self) -> None:
        """Position the dialog over its parent window."""
        self.update_idletasks()
        try:
            px, py = self.master.winfo_rootx(), self.master.winfo_rooty()
            pw, ph = self.master.winfo_width(), self.master.winfo_height()
            w, h = self.winfo_width(), self.winfo_height()
            self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")
        except Exception:  # noqa: BLE001 - centring is best-effort
            pass

    def _confirm(self) -> None:
        self.selection = self._menu.get()
        self.grab_release()
        self.destroy()

    def _cancel(self) -> None:
        self.selection = None
        self.grab_release()
        self.destroy()

    def show(self) -> Optional[str]:
        """Block until the dialog closes and return the selection."""
        self.wait_window()
        return self.selection
