"""Shared, observable application state for the GUI.

A single :class:`AppState` instance is created by the main window and passed to
every page. Pages read and mutate it and can subscribe to change notifications
so, for example, the Dashboard refreshes automatically when a new Excel file is
loaded. This keeps pages decoupled from one another.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from core.models import ColumnMapping
from utils.logger import get_logger

logger = get_logger(__name__)

# A listener is called with the name of the state attribute that changed.
Listener = Callable[[str], None]


class AppState:
    """Mutable state shared across GUI pages with a simple observer pattern.

    Attributes:
        excel_path: Absolute path to the selected workbook, if any.
        sheet_names: Worksheet names available in the selected workbook.
        worksheet: Currently selected worksheet name.
        headers: Column headers read from the selected worksheet.
        record_count: Number of data rows loaded.
        mapping: Active column mapping (canonical key -> source column).
        selected_rules: Set of enabled rule ids.
        active_profile: Name of the loaded profile, if any.
    """

    def __init__(self) -> None:
        self.excel_path: Optional[str] = None
        self.sheet_names: list[str] = []
        self.worksheet: Optional[str] = None
        self.headers: list[str] = []
        self.record_count: int = 0
        self.mapping: ColumnMapping = ColumnMapping()
        self.selected_rules: set[str] = set()
        self.active_profile: Optional[str] = None
        # Opaque handle to the loaded dataset (a pandas DataFrame in Phase 3).
        self.dataframe: Any = None
        self.agent_analysis: Any = None
        self.questionnaire_path: Optional[str] = None
        self.questionnaire_text: str = ""
        self._listeners: list[Listener] = []

    # ----------------------------------------------------------------- #
    # Observer plumbing
    # ----------------------------------------------------------------- #
    def subscribe(self, listener: Listener) -> None:
        """Register ``listener`` to be called whenever state changes."""
        self._listeners.append(listener)

    def notify(self, field: str) -> None:
        """Notify all listeners that ``field`` changed."""
        for listener in list(self._listeners):
            try:
                listener(field)
            except Exception:  # noqa: BLE001 - a bad listener must not crash others
                logger.exception("State listener failed for field '%s'.", field)

    # ----------------------------------------------------------------- #
    # Convenience mutators (each notifies subscribers)
    # ----------------------------------------------------------------- #
    def set_workbook(self, path: str, sheet_names: list[str]) -> None:
        """Record a newly selected workbook and reset dependent state."""
        self.excel_path = path
        self.sheet_names = sheet_names
        self.worksheet = None
        self.headers = []
        self.record_count = 0
        self.dataframe = None
        self.notify("excel_path")

    def set_questionnaire(self, path: str, text: str) -> None:
        """Store the extracted project questionnaire context."""
        self.questionnaire_path = path
        self.questionnaire_text = text
        self.notify("questionnaire")

    def set_loaded_sheet(
        self, worksheet: str, headers: list[str], record_count: int, dataframe: Any
    ) -> None:
        """Record the loaded worksheet's headers, row count and data."""
        self.worksheet = worksheet
        self.headers = headers
        self.record_count = record_count
        self.dataframe = dataframe
        self.notify("worksheet")

    @property
    def has_data(self) -> bool:
        """Return ``True`` once a worksheet has been loaded with headers."""
        return bool(self.headers)
