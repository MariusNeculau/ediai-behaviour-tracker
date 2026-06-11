# System Settings (DB-backed) — Design Spec

**Date:** 2026-06-11
**Status:** Approved (pending spec review)
**Branch:** `feature/settings-crud` work continues on `main` (Settings CRUD already merged)

## Problem

School identity (`name`, `roll_number`) is currently hardcoded in `config.py` and
served to the dashboard as a read-only info box. For an enterprise-ready product a
non-technical user must be able to edit these values without touching code. The data
should persist in the database, not in `config.py`.

## Goal

Move school identity into the database and let the user edit **School Name** and
**Roll Number** from a new **System** section at the top of the Settings page. Both
fields are required. `config.py` remains only as the *initial default* used to seed
the row on first run.

## Non-Goals

- No multi-tenant / multiple schools — exactly one school per install (single row).
- No additional system settings beyond name + roll number in this step.
- No sub-tab navigation inside Settings (a new section, consistent with the existing
  section-based layout).
- No audit log / history of changes.

## Data Model

New single-row table in `models.py`:

```python
class SystemConfig(db.Model):
    __tablename__ = "system_config"
    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(120), nullable=False)
    roll_number = db.Column(db.String(40), nullable=False)
```

- Exactly one row exists. Seeded once from `config.SCHOOL` in `seed_lookups()` if no
  row is present.
- Runtime source of truth for school identity is this row, not `config.SCHOOL`.

## Serialization

New function in `serializers.py`:

```python
def serialize_system_config(sc):
    return {"name": sc.school_name, "roll_number": sc.roll_number}
```

Shape matches the existing `SCHOOL` global usage in the template (`SCHOOL.name`,
`SCHOOL.roll_number`), so Reports headers need no change.

## Backend Wiring (`app.py`)

- `seed_lookups()`: if `SystemConfig.query.first()` is `None`, insert a row from
  `config.SCHOOL` (`school_name=config.SCHOOL["name"]`, `roll_number=config.SCHOOL["roll_number"]`).
- Dashboard route: replace `school=config.SCHOOL` with
  `school=serialize_system_config(SystemConfig.query.first())`.

## API (`settings_api.py`)

A single resource — no create/delete (the row always exists):

- `GET /api/system` → `200` with `{"name": ..., "roll_number": ...}`.
- `PUT /api/system` → update both fields.
  - Validation: `name` required and non-blank → else `400 {"error": "Name is required"}`.
  - Validation: `roll_number` required and non-blank → else `400 {"error": "Roll number is required"}`.
  - On success: `200` with the serialized config.

Both handlers operate on `SystemConfig.query.first()` (guaranteed to exist by seeding).

## Frontend (`templates/dashboard.html`)

- Replace the current read-only School info box at the top of `renderSettings()` with
  an editable **System** section: a `settings-section` containing a School Name input,
  a Roll Number input, and a **Save** button wired to `saveSystem()`.
- `saveSystem()`:
  - Read both inputs, trimmed. If either is blank, `alert` and abort client-side.
  - `PUT /api/system` with `{name, roll_number}`.
  - On non-OK: `alert` the server `error`.
  - On success: mutate `SCHOOL.name` and `SCHOOL.roll_number` (the `const SCHOOL`
    object's properties), `showToast('System settings saved')`, `showTab('settings')`
    to re-render. Reports headers read `SCHOOL.name` at render time, so they reflect
    the new value without a full reload.

## Migration

Schema change (new table). Local dev DB is recreated:

```
if (Test-Path instance/behaviour.db) { Remove-Item instance/behaviour.db -Force }
```

`instance/` is gitignored; no real data is lost. `db.create_all()` creates the new
table and `seed_lookups()` populates the row from `config.SCHOOL`.

## Testing (TDD, `tests/test_settings.py`)

1. `test_get_system_config_defaults` — `GET /api/system` returns the values seeded
   from `config.SCHOOL`.
2. `test_update_system_config` — `PUT /api/system` with new name + roll number returns
   `200`; a follow-up `GET` reflects both new values.
3. `test_update_system_blank_name_returns_400` — blank `name` → `400`.
4. `test_update_system_blank_roll_returns_400` — blank `roll_number` → `400`.
5. `test_dashboard_reflects_system_config` — after `PUT`, rendering `GET /` includes
   the new school name in the HTML (satisfies "reflected in the UI").

## Done Criteria

- `pytest -q` green (existing 27 + new system tests).
- Editing School Name / Roll Number from Settings → System persists to DB and survives
  a server restart.
- Both fields enforced as required (blank → clear error).
- Reports headers show the edited school name without a code change.
