"""Column Mapping page.

Displays every canonical survey field with a dropdown for choosing the matching
spreadsheet column. Auto-detection pre-selects likely matches; the user can
adjust any of them. This page only runs once a worksheet has been loaded.
"""

from __future__ import annotations

import customtkinter as ctk

from core.canonical_fields import CANONICAL_FIELDS
from core.mapping import auto_detect_mapping
from core.models import ColumnMapping
from gui import theme
from gui.pages.base_page import BasePage
from gui.widgets import hint_label

_UNMAPPED = "— Not mapped —"


class ColumnMappingPage(BasePage):
    """Interface for mapping canonical fields to worksheet columns."""

    title = "Column Mapping"

    def build(self) -> None:
        """Create the toolbar and the scrollable list of field rows."""
        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, theme.PAD_S))
        ctk.CTkButton(toolbar, text="Auto-detect", command=self._auto_detect).pack(side="left")
        ctk.CTkButton(
            toolbar, text="Clear all", fg_color="transparent", border_width=1,
            command=self._clear_all,
        ).pack(side="left", padx=theme.PAD_S)
        ctk.CTkButton(toolbar, text="Apply mapping", command=self._apply).pack(side="right")

        hint_label(
            self.body,
            "Match each survey field to the matching column in your file. "
            "Detected matches are pre-filled — adjust any that are wrong. "
            "Save reusable mappings from the Profiles page.",
        ).pack(fill="x", pady=(0, theme.PAD_S))

        inventory = ctk.CTkFrame(self.body, fg_color="transparent")
        inventory.pack(fill="x", pady=(0, theme.PAD_S))
        ctk.CTkLabel(inventory, text="All imported columns", anchor="w").pack(side="left")
        self._column_search = ctk.CTkEntry(
            inventory, width=260, placeholder_text="Search column names"
        )
        self._column_search.pack(side="right")
        self._column_search.bind("<KeyRelease>", lambda _event: self._render_column_inventory())
        self._column_inventory = ctk.CTkTextbox(self.body, height=90, wrap="none")
        self._column_inventory.pack(fill="x", pady=(0, theme.PAD_S))
        self._column_inventory.configure(state="disabled")

        self._scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)
        self._scroll.grid_columnconfigure(1, weight=1)

        self._menus: dict[str, ctk.CTkOptionMenu] = {}
        self._empty = ctk.CTkLabel(
            self.body, text="Load a worksheet first (Dashboard → Select Excel File).",
            text_color=theme.COLOR_MUTED,
        )

    def on_show(self) -> None:
        """Rebuild rows to match the currently loaded worksheet."""
        if not self._built:
            return
        self._render()

    # ----------------------------------------------------------------- #
    # Rendering
    # ----------------------------------------------------------------- #
    def _render(self) -> None:
        """Draw one dropdown row per canonical field, or an empty-state note."""
        for child in self._scroll.winfo_children():
            child.destroy()
        self._menus.clear()

        if not self.state.has_data:
            self._render_column_inventory()
            self._scroll.pack_forget()
            self._empty.pack(pady=theme.PAD_L)
            return

        self._empty.pack_forget()
        self._scroll.pack(fill="both", expand=True)
        self._render_column_inventory()

        options = [_UNMAPPED] + list(self.state.headers)
        for row, field in enumerate(CANONICAL_FIELDS):
            label_text = field.label + (" *" if field.required else "")
            ctk.CTkLabel(self._scroll, text=label_text, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, theme.PAD_M), pady=4
            )
            menu = ctk.CTkOptionMenu(self._scroll, values=options, width=320)
            current = self.state.mapping.source_for(field.key)
            menu.set(current if current in self.state.headers else _UNMAPPED)
            menu.grid(row=row, column=1, sticky="ew", pady=4)
            self._menus[field.key] = menu

    def _render_column_inventory(self) -> None:
        """Display every source header, with an optional name filter."""
        if not hasattr(self, "_column_inventory"):
            return
        query = self._column_search.get().strip().lower()
        headers = [
            header for header in self.state.headers
            if not query or query in header.lower()
        ]
        text = "\n".join(f"{index + 1}. {header}" for index, header in enumerate(headers))
        self._column_inventory.configure(state="normal")
        self._column_inventory.delete("1.0", "end")
        self._column_inventory.insert("1.0", text or "No matching columns.")
        self._column_inventory.configure(state="disabled")

    # ----------------------------------------------------------------- #
    # Actions
    # ----------------------------------------------------------------- #
    def _collect(self) -> ColumnMapping:
        """Read the dropdowns into a :class:`ColumnMapping`."""
        mapping = {
            key: (None if menu.get() == _UNMAPPED else menu.get())
            for key, menu in self._menus.items()
        }
        return ColumnMapping(mapping)

    def _apply(self) -> None:
        """Store the current dropdown selections into shared state."""
        if not self.state.has_data:
            return
        self.state.mapping = self._collect()
        count = len(self.state.mapping.mapped_keys())
        self.set_status(f"Applied mapping for {count} field(s).", "success")

    def _auto_detect(self) -> None:
        """Re-run automatic detection and refresh the dropdowns."""
        if not self.state.has_data:
            return
        self.state.mapping = auto_detect_mapping(self.state.headers)
        self._render()
        count = len(self.state.mapping.mapped_keys())
        self.set_status(f"Auto-detected {count} field(s).", "info")

    def _clear_all(self) -> None:
        """Reset every dropdown to unmapped."""
        for menu in self._menus.values():
            menu.set(_UNMAPPED)
