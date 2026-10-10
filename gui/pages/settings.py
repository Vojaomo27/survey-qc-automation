"""Settings page.

Exposes appearance (light/dark/system + colour theme) and project metadata
(QC officer, project name, output folder). All values persist to the user
configuration. Appearance changes apply immediately.
"""

from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from gui import theme
from gui.pages.base_page import BasePage
from gui.widgets import SectionTitle, hint_label
from utils.constants import APPEARANCE_MODES, COLOR_THEMES


class SettingsPage(BasePage):
    """Editable application settings."""

    title = "Settings"

    def build(self) -> None:
        """Create appearance and project-metadata controls."""
        SectionTitle(self.body, "Appearance").pack(anchor="w", pady=(0, theme.PAD_S))

        appearance_row = ctk.CTkFrame(self.body, fg_color="transparent")
        appearance_row.pack(fill="x")
        ctk.CTkLabel(appearance_row, text="Mode", width=140, anchor="w").pack(side="left")
        self._mode = ctk.CTkOptionMenu(
            appearance_row, values=list(APPEARANCE_MODES), command=self._change_mode
        )
        self._mode.set(self.config.get_setting("appearance_mode", "System"))
        self._mode.pack(side="left")

        theme_row = ctk.CTkFrame(self.body, fg_color="transparent")
        theme_row.pack(fill="x", pady=(theme.PAD_S, 0))
        ctk.CTkLabel(theme_row, text="Colour theme", width=140, anchor="w").pack(side="left")
        self._theme = ctk.CTkOptionMenu(theme_row, values=list(COLOR_THEMES))
        self._theme.set(self.config.get_setting("color_theme", "dark-blue"))
        self._theme.pack(side="left")
        hint_label(self.body, "Colour theme applies after restarting the app.").pack(
            anchor="w", pady=(2, theme.PAD_M)
        )

        SectionTitle(self.body, "Project details").pack(anchor="w", pady=(theme.PAD_M, theme.PAD_S))
        self._qc_officer = self._text_row("QC Officer", self.config.get_setting("qc_officer", ""))
        self._project = self._text_row("Project name", self.config.get_setting("project_name", ""))

        out_row = ctk.CTkFrame(self.body, fg_color="transparent")
        out_row.pack(fill="x", pady=theme.PAD_S)
        ctk.CTkLabel(out_row, text="Output folder", width=140, anchor="w").pack(side="left")
        self._output = ctk.CTkEntry(out_row, width=360)
        self._output.insert(0, self.config.get_setting("output_folder", ""))
        self._output.pack(side="left", padx=(0, theme.PAD_S))
        ctk.CTkButton(out_row, text="Browse", width=80, command=self._browse_output).pack(side="left")

        self._auto_open = ctk.CTkCheckBox(self.body, text="Open report automatically after generation")
        if self.config.get_setting("auto_open_report", True):
            self._auto_open.select()
        self._auto_open.pack(anchor="w", pady=theme.PAD_M)

        SectionTitle(self.body, "Agent advisor").pack(anchor="w", pady=(theme.PAD_M, theme.PAD_S))
        self._llm_provider = ctk.CTkOptionMenu(
            self.body,
            values=["google_ai_studio", "groq", "none"],
            width=360,
        )
        self._llm_provider.set(self.config.get_setting("llm_provider", "google_ai_studio"))
        self._llm_provider.pack(anchor="w", pady=(0, theme.PAD_S))

        self._llm_model = self._text_row(
            "Model", self.config.get_setting("llm_model", "gemini-2.5-flash")
        )
        self._llm_endpoint = self._text_row(
            "Endpoint", self.config.get_setting(
                "llm_endpoint", "https://generativelanguage.googleapis.com/v1beta/openai"
            )
        )
        self._llm_api_key = self._secret_row("AI API key")
        hint_label(
            self.body,
            "Paste the current provider key above. It is saved locally in config/llm_api_key.txt and never logged.",
        ).pack(anchor="w", pady=(0, theme.PAD_M))

        ctk.CTkButton(self.body, text="Save settings", command=self._save).pack(anchor="w")

    def _text_row(self, label: str, value: str) -> ctk.CTkEntry:
        """Create a labelled text entry row and return the entry."""
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=theme.PAD_S)
        ctk.CTkLabel(row, text=label, width=140, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row, width=360)
        entry.insert(0, value)
        entry.pack(side="left")
        return entry

    def _secret_row(self, label: str) -> ctk.CTkEntry:
        """Create a masked API-key field with a hidden saved-key placeholder."""
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=theme.PAD_S)
        ctk.CTkLabel(row, text=label, width=140, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row, width=360, show="*", placeholder_text="Paste a new key to replace the saved key")
        entry.pack(side="left", padx=(0, theme.PAD_S))
        ctk.CTkButton(row, text="Clear", width=70, command=self._clear_llm_key).pack(side="left")
        return entry

    def _clear_llm_key(self) -> None:
        """Remove the saved API key and clear the visible field."""
        self._llm_api_key.delete(0, "end")
        self.config.set_llm_api_key("")
        self.set_status("LLM API key cleared.", "success")

    # ----------------------------------------------------------------- #
    # Actions
    # ----------------------------------------------------------------- #
    def _change_mode(self, mode: str) -> None:
        """Apply the appearance mode immediately."""
        ctk.set_appearance_mode(mode)

    def _browse_output(self) -> None:
        """Choose an output folder."""
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self._output.delete(0, "end")
            self._output.insert(0, folder)

    def _save(self) -> None:
        """Persist all settings to the user configuration."""
        self.config.set_setting("appearance_mode", self._mode.get())
        self.config.set_setting("color_theme", self._theme.get())
        self.config.set_setting("qc_officer", self._qc_officer.get().strip())
        self.config.set_setting("project_name", self._project.get().strip())
        self.config.set_setting("output_folder", self._output.get().strip())
        self.config.set_setting("auto_open_report", bool(self._auto_open.get()))
        self.config.set_setting("llm_provider", self._llm_provider.get().strip() or "google_ai_studio")
        provider = self.config.get_setting("llm_provider", "google_ai_studio")
        if provider == "groq":
            self.config.set_setting("llm_model", self._llm_model.get().strip() or "openai/gpt-oss-120b")
            self.config.set_setting("llm_endpoint", self._llm_endpoint.get().strip() or "https://api.groq.com/openai/v1")
        elif provider == "none":
            self.config.set_setting("llm_model", "")
            self.config.set_setting("llm_endpoint", "")
        else:
            self.config.set_setting("llm_model", self._llm_model.get().strip() or "gemini-2.5-flash")
            self.config.set_setting("llm_endpoint", self._llm_endpoint.get().strip() or "https://generativelanguage.googleapis.com/v1beta/openai")
        if self._llm_api_key.get().strip():
            self.config.set_llm_api_key(self._llm_api_key.get())
        self.config.save()
        self.set_status("Settings saved.", "success")
