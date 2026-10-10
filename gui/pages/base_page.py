"""Base class for all GUI pages.

Every sidebar destination is a :class:`BasePage` — a themed frame with a title
header and a body area. The controller (the main window) is injected so pages
can access shared state, configuration, navigation and the status bar without
importing the app module (avoiding circular imports).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from gui import theme

if TYPE_CHECKING:  # pragma: no cover - typing only
    from config.config_manager import ConfigManager
    from gui.app import SurveyQCApp
    from gui.app_state import AppState


class BasePage(ctk.CTkFrame):
    """Common scaffold shared by every page.

    Subclasses implement :meth:`build` to populate :attr:`body` and may override
    :meth:`on_show` to refresh dynamic content each time the page is displayed.

    Attributes:
        controller: The main application window.
        title: Page title shown in the header.
    """

    #: Overridden by subclasses to set the header text.
    title: str = "Page"

    def __init__(self, master: ctk.CTkBaseClass, controller: "SurveyQCApp") -> None:
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self._built = False

        header = ctk.CTkLabel(self, text=self.title, font=ctk.CTkFont(*theme.FONT_TITLE))
        header.pack(anchor="w", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_S))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=theme.PAD_L, pady=(0, theme.PAD_L))

    # ----------------------------------------------------------------- #
    # Convenience accessors
    # ----------------------------------------------------------------- #
    @property
    def config(self) -> "ConfigManager":
        """Return the shared configuration manager."""
        return self.controller.config

    @property
    def state(self) -> "AppState":
        """Return the shared application state."""
        return self.controller.app_state

    def set_status(self, message: str, level: str = "info") -> None:
        """Proxy to the controller's status bar."""
        self.controller.set_status(message, level)

    # ----------------------------------------------------------------- #
    # Lifecycle hooks
    # ----------------------------------------------------------------- #
    def ensure_built(self) -> None:
        """Build the page's widgets once, lazily."""
        if not self._built:
            self.build()
            self._built = True

    def build(self) -> None:
        """Create the page's widgets. Overridden by subclasses."""

    def on_show(self) -> None:
        """Called each time the page becomes visible. Override to refresh."""
