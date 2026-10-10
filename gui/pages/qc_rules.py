"""QC Rules page.

Presents every available QC rule as a checkbox grouped by category. Rules are
read from the auto-populated :data:`RULE_REGISTRY`, so any rule added in Phase 5
(or later) appears here automatically with no page changes.
"""

from __future__ import annotations

import customtkinter as ctk

from gui import theme
from gui.pages.base_page import BasePage
from gui.widgets import hint_label
from rules import discover_rules
from rules.base_rule import RULE_REGISTRY

# Ensure rule modules are imported even if the registry was not populated yet.
discover_rules()


class QCRulesPage(BasePage):
    """Checkbox list of selectable QC rules, grouped by category."""

    title = "QC Rules"

    def build(self) -> None:
        """Create the toolbar and scrollable, grouped checkbox list."""
        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, theme.PAD_S))
        ctk.CTkButton(toolbar, text="Select all", command=lambda: self._set_all(True)).pack(side="left")
        ctk.CTkButton(
            toolbar, text="Clear all", fg_color="transparent", border_width=1,
            command=lambda: self._set_all(False),
        ).pack(side="left", padx=theme.PAD_S)
        self._count_label = ctk.CTkLabel(toolbar, text="", text_color=theme.COLOR_MUTED)
        self._count_label.pack(side="right")

        hint_label(
            self.body,
            "Tick the checks to run. Each rule is an independent module; new "
            "rules appear here automatically once added.",
        ).pack(fill="x", pady=(0, theme.PAD_S))

        self._scroll = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)
        self._vars: dict[str, ctk.BooleanVar] = {}

    def on_show(self) -> None:
        """Rebuild the checkbox list to reflect the current registry/state."""
        if self._built:
            self._render()

    # ----------------------------------------------------------------- #
    # Rendering
    # ----------------------------------------------------------------- #
    def _render(self) -> None:
        """Draw grouped checkboxes for every registered rule."""
        for child in self._scroll.winfo_children():
            child.destroy()
        self._vars.clear()

        rules = sorted(RULE_REGISTRY.values(), key=lambda r: (r.category, r.name))
        if not rules:
            ctk.CTkLabel(
                self._scroll,
                text="No QC rules are available. Check the installation or rule configuration.",
                text_color=theme.COLOR_MUTED,
            ).pack(anchor="w", pady=theme.PAD_M)
            self._update_count()
            return

        current_category = None
        for rule in rules:
            if rule.category != current_category:
                current_category = rule.category
                ctk.CTkLabel(
                    self._scroll, text=current_category.upper(),
                    font=ctk.CTkFont(*theme.FONT_SMALL), text_color=theme.COLOR_MUTED,
                ).pack(anchor="w", pady=(theme.PAD_M, 2))

            default_on = rule.rule_id in self.state.selected_rules or (
                not self.state.selected_rules and rule.default_enabled
            )
            var = ctk.BooleanVar(value=default_on)
            var.trace_add("write", lambda *_: self._update_count())
            self._vars[rule.rule_id] = var
            ctk.CTkCheckBox(
                self._scroll, text=f"{rule.name}", variable=var,
                command=self._sync_state,
            ).pack(anchor="w", padx=theme.PAD_M, pady=2)

        self._sync_state()

    # ----------------------------------------------------------------- #
    # Actions
    # ----------------------------------------------------------------- #
    def _sync_state(self) -> None:
        """Persist the selected rule ids into shared state."""
        self.state.selected_rules = {rid for rid, var in self._vars.items() if var.get()}
        self._update_count()

    def _set_all(self, value: bool) -> None:
        """Check or uncheck every rule."""
        for var in self._vars.values():
            var.set(value)
        self._sync_state()

    def _update_count(self) -> None:
        """Update the 'N of M selected' label."""
        selected = sum(1 for v in self._vars.values() if v.get())
        self._count_label.configure(text=f"{selected} of {len(self._vars)} selected")
