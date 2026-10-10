"""Automatic column-to-field detection.

Given the raw headers read from a worksheet, :func:`auto_detect_mapping` guesses
which canonical field each column corresponds to using the alias lists declared
in :mod:`core.canonical_fields`. This is pure, side-effect-free logic reused by
the mapping page and by profile handling.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from core.canonical_fields import CANONICAL_FIELDS
from core.models import ColumnMapping


def _normalise(text: str) -> str:
    """Lower-case ``text`` and strip everything except alphanumerics.

    This lets ``"GPS Latitude"``, ``"gps_lat"`` and ``"GPSLat"`` compare equal
    at the fragment level.
    """
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def auto_detect_mapping(headers: list[str]) -> ColumnMapping:
    """Build a best-effort :class:`ColumnMapping` from worksheet ``headers``.

    Each canonical field is matched to the first unused header whose normalised
    form equals or contains one of the field's aliases. Exact matches are
    preferred over substring matches to avoid greedy mis-assignments.

    Args:
        headers: Column headers exactly as they appear in the worksheet.

    Returns:
        A :class:`ColumnMapping`; unmatched fields are simply absent.
    """
    normalised = {header: _normalise(header) for header in headers}
    used: set[str] = set()
    mapping: dict[str, str | None] = {}

    for field in CANONICAL_FIELDS:
        best_header: str | None = None
        best_score = 0.0
        for header in headers:
            if header in used:
                continue
            norm = normalised[header]
            for alias in field.aliases:
                alias_norm = _normalise(alias)
                if not alias_norm:
                    continue
                if norm == alias_norm:
                    score = 3.0
                elif alias_norm in norm:
                    score = 2.0
                else:
                    score = SequenceMatcher(None, norm, alias_norm).ratio()
                    if score < 0.86:
                        continue
                if score > best_score:
                    best_header, best_score = header, score
            if best_score == 3.0:
                break
        if best_header is not None:
            mapping[field.key] = best_header
            used.add(best_header)

    return ColumnMapping(mapping)
