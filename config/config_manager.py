"""Configuration management.

Loads the packaged :data:`DEFAULT_CONFIG_FILE`, deep-merges any user overrides
from :data:`USER_CONFIG_FILE`, and exposes typed access to ``settings`` and
``thresholds``. All user-editable values (appearance, thresholds, output folder,
QC officer, etc.) live here so that end users never touch Python code.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from utils.constants import DEFAULT_CONFIG_FILE, LLM_API_KEY_FILE, USER_CONFIG_FILE, ensure_runtime_dirs
from utils.exceptions import ConfigError
from utils.logger import get_logger

logger = get_logger(__name__)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``.

    Args:
        base: Baseline dictionary (defaults).
        override: Values that take precedence.

    Returns:
        A new merged dictionary; inputs are not mutated.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class ConfigManager:
    """Loads, exposes and persists application configuration.

    Attributes:
        data: The merged configuration dictionary.
    """

    def __init__(self) -> None:
        ensure_runtime_dirs()
        self.data: dict[str, Any] = {}
        self.load()

    # ----------------------------------------------------------------- #
    # Load / save
    # ----------------------------------------------------------------- #
    def load(self) -> None:
        """Load defaults and merge user overrides.

        Raises:
            ConfigError: If the default configuration is missing or malformed.
        """
        try:
            defaults = json.loads(DEFAULT_CONFIG_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigError(
                f"Default configuration not found: {DEFAULT_CONFIG_FILE}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Default configuration is not valid JSON: {exc}") from exc

        user_overrides: dict[str, Any] = {}
        if USER_CONFIG_FILE.exists():
            try:
                user_overrides = json.loads(USER_CONFIG_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("User config is corrupt; ignoring overrides.")
                user_overrides = {}

        self.data = _deep_merge(defaults, user_overrides)
        logger.info("Configuration loaded (user overrides: %s).", bool(user_overrides))

    def save(self) -> None:
        """Persist the current configuration to :data:`USER_CONFIG_FILE`.

        Raises:
            ConfigError: If the file cannot be written.
        """
        try:
            USER_CONFIG_FILE.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("Configuration saved to %s", USER_CONFIG_FILE)
        except OSError as exc:
            raise ConfigError(f"Could not save configuration: {exc}") from exc

    # ----------------------------------------------------------------- #
    # Typed accessors
    # ----------------------------------------------------------------- #
    @property
    def settings(self) -> dict[str, Any]:
        """Return the ``settings`` section."""
        return self.data.setdefault("settings", {})

    @property
    def thresholds(self) -> dict[str, Any]:
        """Return the ``thresholds`` section."""
        return self.data.setdefault("thresholds", {})

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Return a single setting value."""
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Set a single setting value (call :meth:`save` to persist)."""
        self.settings[key] = value

    def get_threshold(self, key: str, default: Any = None) -> Any:
        """Return a single threshold value."""
        return self.thresholds.get(key, default)

    def set_threshold(self, key: str, value: Any) -> None:
        """Set a single threshold value (call :meth:`save` to persist)."""
        self.thresholds[key] = value

    def get_llm_api_key(self) -> str:
        """Read the locally stored LLM key without logging or exposing it."""
        try:
            return LLM_API_KEY_FILE.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""

    def set_llm_api_key(self, value: str) -> None:
        """Replace or clear the locally stored LLM key."""
        if value.strip():
            LLM_API_KEY_FILE.write_text(value.strip(), encoding="utf-8")
        elif LLM_API_KEY_FILE.exists():
            LLM_API_KEY_FILE.unlink()
