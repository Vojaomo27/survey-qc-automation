# Survey QC Automation Tool

A professional desktop application that automates **Quality Control (QC) checks**
on survey datasets stored in Microsoft Excel files. Designed for non-technical
field/data teams: open the app, pick a file, map columns, choose checks, click
one button, and receive a professionally formatted QC report.

> **Status:** Phase 1 (Project Architecture) complete. GUI, data loading, rule
> engine, and reporting are delivered in subsequent phases.

---

## Key Features (target)

- Modern CustomTkinter GUI with light/dark mode and a sidebar workflow.
- Automatic Excel header detection and reusable **column-mapping profiles**.
- Extensible **rule engine** — each QC check is an independent, self-registering class.
- In-memory **SQLite** query engine with threshold values injected at runtime.
- Professionally formatted, single-sheet **Excel QC report** with summary + sections.
- Full logging, graceful error handling, and PyInstaller packaging to `SurveyQC.exe`.

## Technology Stack

Python 3.12 · CustomTkinter · Pandas · SQLite (in-memory) · OpenPyXL ·
SQLAlchemy (where useful) · PyInstaller · standard `logging` · JSON configuration.

---

## Project Structure

```
Master QC tool/
├── main.py               # Application entry point (bootstrap + launch)
├── requirements.txt      # Runtime dependencies
├── README.md
├── gui/                  # CustomTkinter interface           (Phase 2)
├── core/                 # Domain models, canonical fields, orchestration
│   ├── models.py         # ColumnMapping, RuleResult, CanonicalField, ...
│   └── canonical_fields.py  # Registry of known survey fields
├── database/             # In-memory SQLite engine            (Phase 4)
├── rules/                # QC rules (one class per check)     (Phase 5)
│   ├── base_rule.py      # Abstract BaseRule + auto-registry
│   └── __init__.py       # Automatic rule discovery
├── report/               # Excel report generator             (Phase 6)
├── config/               # Configuration + profiles
│   ├── default_config.json  # Default settings & thresholds
│   └── config_manager.py    # Load / merge / save configuration
├── utils/                # Cross-cutting helpers
│   ├── constants.py      # Paths & app metadata (PyInstaller-aware)
│   ├── logger.py         # Logging setup + per-run summary
│   └── exceptions.py     # Custom exception hierarchy
├── assets/               # Icons and images
├── logs/                 # Timestamped run logs (generated)
├── input/                # Suggested location for source Excel files
├── output/               # Generated QC reports (generated)
└── tests/                # Unit / smoke tests
```

## Architecture at a Glance

The application is organised in clean layers with one-directional dependencies:

```
GUI  ──▶  Core (orchestration + models)  ──▶  Database engine
                     │                              ▲
                     ├──▶  Rules (registry) ────────┘
                     └──▶  Report generator
Config & Utils are shared foundations used by every layer.
```

**Design principles**

- **Canonical fields decouple rules from spreadsheets.** Rules reference stable
  keys (e.g. `instance_id`); the column mapping connects those keys to whatever
  the survey actually called its columns.
- **Rules self-register.** Any `BaseRule` subclass added to the `rules/` package
  is discovered automatically — no central list to maintain.
- **No hard-coded values.** Paths live in `utils/constants.py`; thresholds and
  settings live in JSON and are fully editable from the GUI.
- **Fail-soft.** A single failing rule is isolated and reported as *skipped*
  rather than aborting the whole run.
- **PyInstaller-aware paths.** Runtime folders resolve correctly whether running
  from source or from a frozen executable.

---

## Getting Started (development)

```bash
# 1. (optional) create a virtual environment
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash

# 2. install dependencies
pip install -r requirements.txt

# 3. run
python main.py

# 4. run tests
python -m pytest tests/ -v
```

Until the GUI arrives in Phase 2, `python main.py` initialises the runtime
environment and prints a confirmation message.

---

## Roadmap

| Phase | Deliverable            | Status |
|------:|------------------------|--------|
| 1     | Project architecture   | ✅ Done |
| 2     | GUI                    | ✅ Done |
| 3     | Excel loader           | ⏳ Pending |
| 4     | SQLite engine          | ⏳ Pending |
| 5     | Rule engine + rules    | ⏳ Pending |
| 6     | Report generator       | ⏳ Pending |
| 7     | Profiles               | ⏳ Pending |
| 8     | Settings               | ⏳ Pending |
| 9     | Packaging (`SurveyQC.exe`) | ⏳ Pending |
