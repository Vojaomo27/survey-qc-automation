"""Centralised logging configuration.

Every application run creates a timestamped log file inside ``logs/`` and also
streams messages to the console. The :class:`RunLogSummary` helper tracks the
per-run metadata required by the specification (input filename, execution time,
records processed, error/warning counts).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from utils.constants import APP_SHORT_NAME, LOGS_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Track whether the root logging configuration has already been applied so that
# repeated calls (e.g. in tests) do not attach duplicate handlers.
_configured: bool = False


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure application-wide logging.

    Attaches a rotating file handler (one timestamped file per run) and a
    console handler to the root logger. Safe to call multiple times.

    Args:
        level: Minimum logging level for the handlers.

    Returns:
        Path to the log file created for this run.
    """
    global _configured

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"{APP_SHORT_NAME}_{timestamp}.log"

    root = logging.getLogger()
    root.setLevel(level)

    if not _configured:
        formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)

        root.addHandler(file_handler)
        root.addHandler(console_handler)
        _configured = True

    logging.getLogger(__name__).info("Logging initialised -> %s", log_file)
    return log_file


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.

    Args:
        name: Usually ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)


@dataclass
class RunLogSummary:
    """Captures per-run execution metadata for auditing and the report footer.

    Attributes:
        input_filename: Name of the Excel file processed.
        started_at: Wall-clock start time.
        records_processed: Number of survey records loaded.
        errors: Count of errors encountered during the run.
        warnings: Count of warnings encountered during the run.
        rules_run: Number of QC rules executed.
    """

    input_filename: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    records_processed: int = 0
    errors: int = 0
    warnings: int = 0
    rules_run: int = 0
    _start_perf: float = field(default_factory=time.perf_counter, repr=False)

    def execution_seconds(self) -> float:
        """Return elapsed wall-clock seconds since the run started."""
        return round(time.perf_counter() - self._start_perf, 3)

    def as_dict(self) -> dict[str, object]:
        """Return a serialisable summary of the run."""
        return {
            "input_filename": self.input_filename,
            "started_at": self.started_at.strftime(_DATE_FORMAT),
            "execution_seconds": self.execution_seconds(),
            "records_processed": self.records_processed,
            "rules_run": self.rules_run,
            "errors": self.errors,
            "warnings": self.warnings,
        }
