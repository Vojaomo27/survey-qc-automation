"""Main application window.

Assembles the sidebar navigation, the switchable page workspace, a progress bar
and a status bar into a single resizable CustomTkinter window. Pages are created
lazily and reused. The window also hosts the top-level workflow action of
selecting an Excel file.

Note:
    The lightweight worksheet/header reading used by :meth:`select_excel_file`
    is a temporary bridge so the GUI is demonstrable in Phase 2; it is replaced
    by the robust :mod:`database`/Excel loader in Phase 3.
"""

from __future__ import annotations

import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from config.config_manager import ConfigManager
from gui import theme
from gui.app_state import AppState
from gui.dialogs import WorksheetDialog
from gui.pages.about import AboutPage
from gui.pages.agent_advisor import AgentAdvisorPage
from gui.pages.base_page import BasePage
from gui.pages.column_mapping import ColumnMappingPage
from gui.pages.dashboard import DashboardPage
from gui.pages.generate_report import GenerateReportPage
from gui.pages.logs import LogsPage
from gui.pages.profiles import ProfilesPage
from gui.pages.qc_rules import QCRulesPage
from gui.pages.settings import SettingsPage
from gui.pages.thresholds import ThresholdsPage
from utils.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_WINDOW_SIZE,
    MIN_WINDOW_SIZE,
    OUTPUT_DIR,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Sidebar entries: (label, icon glyph, page class).
_NAV: tuple[tuple[str, str, type[BasePage]], ...] = (
    ("Dashboard", "🏠", DashboardPage),
    ("Column Mapping", "🔗", ColumnMappingPage),
    ("QC Rules", "✅", QCRulesPage),
    ("Thresholds", "🎚", ThresholdsPage),
    ("Profiles", "📁", ProfilesPage),
    ("Generate Report", "⚙", GenerateReportPage),
    ("Settings", "⚙️", SettingsPage),
    ("Logs", "📜", LogsPage),
    ("About", "ℹ️", AboutPage),
    ("Agent Advisor", "💡", AgentAdvisorPage),
)

_STATUS_COLORS = {
    "info": theme.COLOR_MUTED,
    "success": theme.COLOR_SUCCESS,
    "warning": theme.COLOR_WARNING,
    "error": theme.COLOR_ERROR,
}


class SurveyQCApp(ctk.CTk):
    """The main application window and navigation controller.

    Attributes:
        config: Shared configuration manager.
        state: Shared, observable application state.
    """

    def __init__(self, config: ConfigManager) -> None:
        super().__init__()
        self.config = config
        self.app_state = AppState()

        ctk.set_appearance_mode(config.get_setting("appearance_mode", "System"))
        try:
            ctk.set_default_color_theme(config.get_setting("color_theme", "dark-blue"))
        except Exception:  # noqa: BLE001 - fall back to library default theme
            logger.warning("Unknown colour theme; using default.")

        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry(f"{DEFAULT_WINDOW_SIZE[0]}x{DEFAULT_WINDOW_SIZE[1]}")
        self.minsize(*MIN_WINDOW_SIZE)

        self._pages: dict[str, BasePage] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._current: str | None = None

        self._build_layout()
        self.show_page("Dashboard")

    # ----------------------------------------------------------------- #
    # Layout
    # ----------------------------------------------------------------- #
    def _build_layout(self) -> None:
        """Create the sidebar, workspace, progress bar and status bar."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

        # Workspace container where pages are swapped in and out.
        self._workspace = ctk.CTkFrame(self, fg_color="transparent")
        self._workspace.grid(row=0, column=1, sticky="nsew")
        self._workspace.grid_rowconfigure(0, weight=1)
        self._workspace.grid_columnconfigure(0, weight=1)

        self._build_statusbar()

    def _build_sidebar(self) -> None:
        """Build the fixed-width navigation sidebar."""
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=theme.COLOR_SIDEBAR)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="Survey QC", font=ctk.CTkFont(*theme.FONT_HEADING),
        ).pack(anchor="w", padx=theme.PAD_L, pady=(theme.PAD_L, theme.PAD_M))

        for label, icon, _ in _NAV:
            btn = ctk.CTkButton(
                sidebar, text=f"  {icon}   {label}", anchor="w", height=38,
                corner_radius=theme.CORNER_RADIUS, fg_color="transparent",
                text_color=("gray10", "gray90"), hover_color=theme.COLOR_PRIMARY_HOVER,
                command=lambda name=label: self.show_page(name),
            )
            btn.pack(fill="x", padx=theme.PAD_S, pady=2)
            self._nav_buttons[label] = btn

        # Appearance toggle pinned to the bottom of the sidebar.
        ctk.CTkLabel(sidebar, text="Appearance", text_color=theme.COLOR_MUTED).pack(
            side="bottom", anchor="w", padx=theme.PAD_L, pady=(0, 0)
        )
        toggle = ctk.CTkOptionMenu(
            sidebar, values=["System", "Light", "Dark"], command=self._on_appearance_change,
        )
        toggle.set(self.config.get_setting("appearance_mode", "System"))
        toggle.pack(side="bottom", fill="x", padx=theme.PAD_S, pady=(theme.PAD_S, theme.PAD_L))

    def _build_statusbar(self) -> None:
        """Build the bottom progress + status bar."""
        bar = ctk.CTkFrame(self, height=34, corner_radius=0)
        bar.grid(row=1, column=1, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            bar, text="Ready.", anchor="w", font=ctk.CTkFont(*theme.FONT_SMALL),
            text_color=theme.COLOR_MUTED,
        )
        self._status_label.grid(row=0, column=0, sticky="w", padx=theme.PAD_M, pady=6)

        self._progress = ctk.CTkProgressBar(bar, width=200)
        self._progress.set(0)
        self._progress.grid(row=0, column=1, sticky="e", padx=theme.PAD_M, pady=6)
        self._progress.grid_remove()  # hidden until a task reports progress

    # ----------------------------------------------------------------- #
    # Navigation
    # ----------------------------------------------------------------- #
    def show_page(self, name: str) -> None:
        """Display the page named ``name``, creating it on first use.

        Args:
            name: Sidebar label of the page to show.
        """
        page = self._pages.get(name)
        if page is None:
            page_cls = next(cls for label, _, cls in _NAV if label == name)
            page = page_cls(self._workspace, self)
            page.grid(row=0, column=0, sticky="nsew")
            page.ensure_built()
            self._pages[name] = page

        if self._current and self._current in self._pages:
            self._pages[self._current].grid_remove()

        page.grid()
        page.on_show()
        self._current = name
        self._highlight_nav(name)

    def _highlight_nav(self, active: str) -> None:
        """Visually mark the active sidebar button."""
        for label, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=theme.COLOR_PRIMARY if label == active else "transparent"
            )

    # ----------------------------------------------------------------- #
    # Status bar / progress
    # ----------------------------------------------------------------- #
    def set_status(self, message: str, level: str = "info") -> None:
        """Update the status bar message.

        Args:
            message: Text to display.
            level: One of ``info``, ``success``, ``warning``, ``error``.
        """
        self._status_label.configure(
            text=message, text_color=_STATUS_COLORS.get(level, theme.COLOR_MUTED)
        )
        logger.log(
            {"error": 40, "warning": 30}.get(level, 20), "Status: %s", message
        )

    def set_progress(self, value: float | None) -> None:
        """Set the progress bar to ``value`` in [0, 1], or hide it if ``None``."""
        if value is None:
            self._progress.grid_remove()
            return
        self._progress.grid()
        self._progress.set(max(0.0, min(1.0, value)))
        self.update_idletasks()

    def _on_appearance_change(self, mode: str) -> None:
        """Handle the sidebar appearance toggle and persist the choice."""
        ctk.set_appearance_mode(mode)
        self.config.set_setting("appearance_mode", mode)
        self.config.save()

    # ----------------------------------------------------------------- #
    # Workflow: Excel selection
    # ----------------------------------------------------------------- #
    def select_excel_file(self) -> None:
        """Prompt for an Excel or SPSS file and load its structure.

        The lightweight read here uses pandas directly as a Phase-2 bridge. In
        Phase 3 this delegates to a dedicated, hardened Excel loader with full
        validation and error handling.
        """
        path = filedialog.askopenfilename(
            title="Select survey data file",
            filetypes=[
                ("Survey data", "*.xlsx *.xlsm *.xls *.sav *.csv"),
                ("Excel workbooks", "*.xlsx *.xlsm *.xls"),
                ("SPSS files", "*.sav"),
                ("CSV files", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            import pandas as pd
            if path.lower().endswith((".sav", ".csv")):
                sheet_names = ["Data"]
            else:
                import pandas as pd

                workbook = pd.ExcelFile(path)
                sheet_names = list(workbook.sheet_names)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            logger.exception("Failed to open workbook.")
            messagebox.showerror("Could not open file", f"Unable to read the workbook:\n{exc}")
            self.set_status("Failed to open workbook.", "error")
            return

        self.app_state.set_workbook(path, sheet_names)

        sheet = sheet_names[0] if path.lower().endswith((".sav", ".csv")) else WorksheetDialog(self, sheet_names).show()
        if not sheet:
            self.set_status("Worksheet selection cancelled.", "info")
            return

        self._load_worksheet(path, sheet)

    def select_questionnaire(self) -> None:
        """Load a project questionnaire or quota PDF before data review."""
        path = filedialog.askopenfilename(
            title="Select questionnaire or quota PDF",
            filetypes=[("PDF documents", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            from core.document_loader import extract_pdf_text

            text = extract_pdf_text(path)
            if not text:
                raise ValueError("No selectable text was found. This PDF may be scanned and require OCR.")
            self.app_state.set_questionnaire(path, text)
            self.set_status(
                f"Questionnaire loaded: {len(text):,} characters. The LLM will use it as study context.",
                "success",
            )
            if "Dashboard" in self._pages:
                self._pages["Dashboard"].on_show()
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            logger.exception("Failed to read questionnaire PDF.")
            messagebox.showerror("Could not read questionnaire", f"{exc}")
            self.set_status("Questionnaire loading failed.", "error")

    def _load_worksheet(self, path: str, sheet: str) -> None:
        """Read a worksheet into state and auto-detect the column mapping."""
        try:
            from core.mapping import auto_detect_mapping
            from core.excel_loader import load_worksheet

            logger.info("[Load 1/4] Reading data file '%s' (sheet: '%s')...", os.path.basename(path), sheet)
            self.set_progress(0.3)
            loaded = load_worksheet(path, sheet)
            dataframe = loaded.dataframe
            headers = [str(c) for c in dataframe.columns]
            logger.info("[Load 2/4] Loaded %d rows and %d columns.", len(dataframe.index), len(headers))
            self.set_progress(0.7)

            self.app_state.set_loaded_sheet(sheet, headers, len(dataframe.index), dataframe)
            self.app_state.mapping = auto_detect_mapping(headers)
            logger.info("[Load 3/4] Auto-mapped %d canonical field(s).", len(self.app_state.mapping.mapped_keys()))
            from core.agent import QCAgent

            self.app_state.agent_analysis = QCAgent().analyze(dataframe, self.app_state.mapping)
            # Keep every default check visible and selected. Rules with missing
            # mappings will report a clear skipped reason in the QC report.
            from rules.base_rule import RULE_REGISTRY

            self.app_state.selected_rules = {
                rule_id for rule_id, rule in RULE_REGISTRY.items() if rule.default_enabled
            }
            logger.info("[Load 4/4] Data understanding complete; ready for QC.")
            self.set_progress(1.0)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            logger.exception("Failed to read worksheet '%s'.", sheet)
            messagebox.showerror("Could not read worksheet", f"{exc}")
            self.set_status("Failed to read worksheet.", "error")
            self.set_progress(None)
            return

        self.set_progress(None)
        mapped = len(self.app_state.mapping.mapped_keys())
        header_note = "metadata" if loaded.header_row < 0 else f"header row {loaded.header_row + 1}"
        self.set_status(
            f"Loaded '{sheet}': {self.app_state.record_count:,} rows, "
            f"{len(self.app_state.headers)} columns, {mapped} field(s) auto-mapped "
            f"({header_note}); data understood before QC.",
            "success",
        )
        # Refresh any pages that depend on the loaded data.
        for name in ("Dashboard", "Column Mapping", "Generate Report"):
            if name in self._pages:
                self._pages[name].on_show()

    def generate_report(self) -> None:
        """Run the agent and save a report for the loaded worksheet."""
        if self.app_state.dataframe is None:
            messagebox.showwarning("No data", "Please load a worksheet before generating a report.")
            return

        try:
            from core.agent import QCAgent
            from report import generate_report as write_report
            from rules.base_rule import RULE_REGISTRY

            logger.info("[Report 1/3] Starting understand-before-QC workflow.")
            agent = QCAgent()
            analysis = agent.analyze(self.app_state.dataframe, self.app_state.mapping)
            self.app_state.agent_analysis = analysis
            selected = self.app_state.selected_rules or {
                rule_id for rule_id, rule in RULE_REGISTRY.items() if rule.default_enabled
            }
            results = agent.run(
                self.app_state.dataframe,
                self.app_state.mapping,
                self.config.thresholds,
                selected,
            )
            logger.info("[Report 2/3] QC complete; preparing Excel report.")
            folder = self.config.get_setting("output_folder") or str(OUTPUT_DIR)
            path = write_report(
                folder,
                self.app_state.excel_path or "survey.xlsx",
                results,
                self.app_state.record_count,
                analysis,
            )
            logger.info("[Report 3/3] Report written to '%s'.", path)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            logger.exception("Failed to generate QC report.")
            messagebox.showerror("Report failed", f"Unable to generate the QC report:\n{exc}")
            self.set_status("Report generation failed.", "error")
            return

        self.set_status(f"Report saved: {path.name}", "success")
        if self.config.get_setting("auto_open_report", True):
            try:
                os.startfile(path)  # type: ignore[attr-defined]
            except OSError:
                logger.info("Report saved but could not be opened automatically: %s", path)
    # ----------------------------------------------------------------- #
    # Entry point
    # ----------------------------------------------------------------- #
    def run(self) -> None:
        """Start the Tk main loop."""
        logger.info("Launching GUI main loop.")
        self.mainloop()
