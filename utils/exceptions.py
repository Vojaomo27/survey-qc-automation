"""Custom exception hierarchy for the Survey QC Automation Tool.

Using a dedicated exception hierarchy lets the GUI and core layers catch and
present errors in a user-friendly way while keeping technical detail in the
logs. Every application-specific error inherits from :class:`SurveyQCError`.
"""

from __future__ import annotations


class SurveyQCError(Exception):
    """Base class for all application-specific errors.

    Attributes:
        message: Human-readable message safe to show to end users.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# --------------------------------------------------------------------------- #
# Configuration / profile errors
# --------------------------------------------------------------------------- #
class ConfigError(SurveyQCError):
    """Raised when configuration cannot be loaded, parsed or saved."""


class ProfileError(SurveyQCError):
    """Raised for invalid profile operations (missing, duplicate, corrupt)."""


# --------------------------------------------------------------------------- #
# Excel / data-loading errors
# --------------------------------------------------------------------------- #
class ExcelLoadError(SurveyQCError):
    """Raised when an Excel workbook cannot be opened or read."""


class EmptySheetError(ExcelLoadError):
    """Raised when a selected worksheet contains no data rows."""


class DuplicateHeaderError(ExcelLoadError):
    """Raised when a worksheet contains duplicate column headers."""


# --------------------------------------------------------------------------- #
# Mapping / rule errors
# --------------------------------------------------------------------------- #
class MappingError(SurveyQCError):
    """Raised when a column mapping is invalid or incomplete for a rule."""


class RuleExecutionError(SurveyQCError):
    """Raised when a QC rule fails to execute."""


# --------------------------------------------------------------------------- #
# Database errors
# --------------------------------------------------------------------------- #
class DatabaseError(SurveyQCError):
    """Raised for failures in the in-memory SQLite engine."""


# --------------------------------------------------------------------------- #
# Report errors
# --------------------------------------------------------------------------- #
class ReportError(SurveyQCError):
    """Raised when the QC report cannot be generated or saved."""
