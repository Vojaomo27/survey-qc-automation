"""Registry of canonical survey fields.

This is the single source of truth for the survey fields the application knows
about. The column-mapping page, the auto-detection logic and every QC rule use
these keys. Adding a new field here makes it available everywhere without any
other code change.
"""

from __future__ import annotations

from core.models import CanonicalField, FieldType

# Ordered registry of every canonical field the tool understands. ``aliases``
# are lower-case fragments matched against normalised spreadsheet headers during
# automatic detection.
CANONICAL_FIELDS: tuple[CanonicalField, ...] = (
    CanonicalField(
        "instance_id", "Instance ID", FieldType.TEXT,
        aliases=("instanceid", "instance id", "instance_id", "uuid", "_uuid",
                 "submissionid", "key", "_id"),
        required=True,
    ),
    CanonicalField(
        "enumerator", "Enumerator", FieldType.TEXT,
        aliases=("enumerator", "interviewer", "surveyor", "collector",
                 "fieldworker", "agent", "staff"),
        required=True,
    ),
    CanonicalField(
        "submission_date", "Submission Date", FieldType.DATETIME,
        aliases=("submissiondate", "submission date", "submitted", "_submission_time",
                 "endtime", "completiondate"),
    ),
    CanonicalField(
        "interview_start", "Interview Start", FieldType.DATETIME,
        aliases=("interviewstart", "starttime", "start time", "start", "begin"),
    ),
    CanonicalField(
        "interview_end", "Interview End", FieldType.DATETIME,
        aliases=("interviewend", "endtime", "end time", "end", "finish"),
    ),
    CanonicalField(
        "interview_duration", "Interview Duration (min)", FieldType.FLOAT,
        aliases=("duration", "interviewduration", "duration_minutes", "durationmin",
                 "length", "elapsed"),
    ),
    CanonicalField(
        "latitude", "GPS Latitude", FieldType.FLOAT,
        aliases=("latitude", "gps_lat", "gpslat", "lat", "_gps_latitude", "y"),
    ),
    CanonicalField(
        "longitude", "GPS Longitude", FieldType.FLOAT,
        aliases=("longitude", "gps_lon", "gpslon", "lon", "lng", "_gps_longitude", "x"),
    ),
    CanonicalField(
        "gps_accuracy", "GPS Accuracy (m)", FieldType.FLOAT,
        aliases=("accuracy", "gps_accuracy", "gpsaccuracy", "precision",
                 "_gps_accuracy"),
    ),
    CanonicalField(
        "household_id", "Household ID", FieldType.TEXT,
        aliases=("householdid", "household id", "household_id", "hhid", "hh_id"),
    ),
    CanonicalField(
        "respondent_name", "Respondent Name", FieldType.TEXT,
        aliases=("respondentname", "respondent", "name", "fullname", "respondent_name"),
    ),
    CanonicalField(
        "village", "Village / Location", FieldType.TEXT,
        aliases=("village", "location", "community", "ward", "settlement", "town"),
    ),
    CanonicalField(
        "consent", "Consent", FieldType.BOOLEAN,
        aliases=("consent", "agree", "agreed", "consent_given", "willing"),
    ),
    CanonicalField(
        "age", "Respondent Age", FieldType.INTEGER,
        aliases=("age", "respondentage", "age_years", "ageyears"),
    ),
    CanonicalField(
        "sex", "Respondent Sex", FieldType.TEXT,
        aliases=("sex", "gender"),
    ),
    CanonicalField(
        "household_size", "Household Size", FieldType.INTEGER,
        aliases=("householdsize", "household size", "hhsize", "hh_size", "members"),
    ),
)

# Fast lookup by key.
CANONICAL_FIELD_MAP: dict[str, CanonicalField] = {f.key: f for f in CANONICAL_FIELDS}


def get_field(key: str) -> CanonicalField:
    """Return the :class:`CanonicalField` for ``key``.

    Args:
        key: Canonical field key.

    Raises:
        KeyError: If ``key`` is not registered.
    """
    return CANONICAL_FIELD_MAP[key]


def field_keys() -> list[str]:
    """Return all canonical field keys in registry order."""
    return [f.key for f in CANONICAL_FIELDS]
