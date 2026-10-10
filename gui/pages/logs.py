"""Logs page.

Shows the most recent lines of the current run's log file so users get feedback
without opening the ``logs/`` folder. A refresh button re-reads the newest file.
"""

from __future__ import annotations

import customtkinter as ctk

from gui import theme
from gui.pages.base_page import BasePage
from utils.constants import APP_SHORT_NAME, LOGS_DIR


class LogsPage(BasePage):
    """Read-only viewer for the latest log file."""

    title = "Logs"

    def build(self) -> None:
        """Create the toolbar and read-only text box."""
        toolbar = ctk.CTkFrame(self.body, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, theme.PAD_S))
        ctk.CTkButton(toolbar, text="Refresh", command=self._load_latest).pack(side="left")
        ctk.CTkButton(
            toolbar, text="Open logs folder", fg_color="transparent", border_width=1,
            command=self._open_folder,
        ).pack(side="left", padx=theme.PAD_S)

        self._textbox = ctk.CTkTextbox(self.body, font=("Consolas", 12))
        self._textbox.pack(fill="both", expand=True)
        self._load_latest()

    def on_show(self) -> None:
        """Reload the latest log lines when shown."""
        if self._built:
            self._load_latest()

    def _latest_log(self):
        """Return the most recently modified log file, or ``None``."""
        files = sorted(
            LOGS_DIR.glob(f"{APP_SHORT_NAME}_*.log"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        return files[0] if files else None

    def _load_latest(self) -> None:
        """Load the tail of the newest log file into the text box."""
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        log_file = self._latest_log()
        if log_file is None:
            self._textbox.insert("1.0", "No log files yet.")
        else:
            try:
                lines = log_file.read_text(encoding="utf-8").splitlines()[-400:]
                self._textbox.insert("1.0", "\n".join(lines))
            except OSError as exc:
                self._textbox.insert("1.0", f"Could not read log file: {exc}")
        self._textbox.configure(state="disabled")

    def _open_folder(self) -> None:
        """Open the logs directory in the OS file explorer."""
        import os
        import subprocess
        import sys

        try:
            if sys.platform.startswith("win"):
                os.startfile(LOGS_DIR)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(LOGS_DIR)], check=False)
            else:
                subprocess.run(["xdg-open", str(LOGS_DIR)], check=False)
        except Exception:  # noqa: BLE001 - best effort convenience action
            self.set_status("Could not open logs folder.", "warning")
