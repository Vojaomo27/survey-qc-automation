"""Survey QC Automation Tool — application entry point.

Responsibilities of this module are deliberately thin: initialise runtime
directories, configure logging, load configuration, then hand control to the
GUI layer. Keeping the bootstrap isolated makes the app easy to test and to
package with PyInstaller.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from config.config_manager import ConfigManager
from rules import discover_rules
from utils.constants import APP_NAME, APP_VERSION, ensure_runtime_dirs
from utils.logger import get_logger, setup_logging


def bootstrap() -> ConfigManager:
    """Prepare the runtime environment and return a loaded config manager.

    Returns:
        A ready-to-use :class:`ConfigManager`.
    """
    print("[Startup 1/3] Preparing runtime directories...")
    ensure_runtime_dirs()
    setup_logging()
    discover_rules()
    logger = get_logger(__name__)
    logger.info("[Startup 2/3] Logging configured.")
    logger.info("Starting %s v%s", APP_NAME, APP_VERSION)
    config = ConfigManager()
    logger.info("[Startup 3/3] Configuration loaded.")
    return config


def main() -> int:
    """Application entry point.

    Returns:
        Process exit code (0 on success).
    """
    config = bootstrap()
    logger = get_logger(__name__)

    try:
        # The GUI layer is introduced in Phase 2. Import lazily so the rest of
        # the application (and its tests) can run before the GUI exists.
        from gui.app import SurveyQCApp

        logger.info("[Startup] Building application interface...")
        app = SurveyQCApp(config)
        logger.info("[Startup] Interface ready. Waiting for a data file.")
        app.run()
    except ImportError:
        logger.warning("GUI layer not available yet (arrives in Phase 2).")
        print(f"{APP_NAME} v{APP_VERSION}")
        print("Core architecture initialised successfully.")
        print("Runtime directories and configuration are ready.")
        print("The graphical interface will be added in Phase 2.")
    except Exception:  # noqa: BLE001 - top-level guard
        logger.exception("Fatal error during application startup.")
        try:
            crash_file = Path(sys.executable).resolve().parent / "startup_error.txt"
            crash_file.write_text(
                "SurveyQC failed during startup:\n\n" + traceback.format_exc(),
                encoding="utf-8",
            )
        except OSError:
            pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
