"""QC rules package.

Importing this package triggers automatic discovery of every rule module so
that each :class:`~rules.base_rule.BaseRule` subclass registers itself in
:data:`~rules.base_rule.RULE_REGISTRY`. Concrete rule modules are added from
Phase 5 onward; discovery is a no-op until then.
"""

from __future__ import annotations

import importlib
import pkgutil

from utils.logger import get_logger

logger = get_logger(__name__)


def discover_rules() -> None:
    """Import every module in this package so rules self-register.

    Modules whose name starts with ``_`` (e.g. ``base_rule`` support files that
    should not be treated as rules) are still imported when needed but the
    ``base_rule`` module is skipped here because it defines only the abstract
    base and registry.
    """
    package_path = __path__  # type: ignore[name-defined]
    for module_info in pkgutil.iter_modules(package_path):
        name = module_info.name
        if name in {"base_rule"}:
            continue
        try:
            importlib.import_module(f"{__name__}.{name}")
        except Exception:  # noqa: BLE001 - never let one bad module break the app
            logger.exception("Failed to import rule module '%s'.", name)


discover_rules()
