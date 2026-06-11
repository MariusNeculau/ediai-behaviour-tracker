# Design: Incident Persistence (create-only)

**Date:** 2026-06-11
**Project:** EDI AI Behaviour Tracker (Local Desktop — Flask/SQLite)
**Status:** Approved (design phase)

## Goal

Make the "Log Incident" form persist to SQLite instead of an in-memory JS
array. Scope is **create-only** (POST); edit and delete are deferred (YAGNI).
The server becomes the source of truth: it returns the persisted incident and
the frontend appends it to its in-memory `INCIDENTS` list (Approach A — AJAX
POST + optimistic update, no full reload).

## Decisions

- **CRUD scope:** create only (`POST /api/incidents`).
- **`notes` field:** add a `notes` column to the `Incident` model (the form
  collects it; the model currently drops it).
- **Demo data:** enable `SEED_DEMO_DATA` with a small set of **generic** demo
  children (no real names) so the form is usable before Settings CRUD exists.
- **Status on save:** incidents logged via the form get `status='Resolved'`
  (matches the original mockup behaviour), even though the model column
  defaults to `'Active'`.
- **Tests:** add a `tests/` folder; pytest as a dev dependency. TDD — tests
  written before implementation.

## Components

### 1. Model — `models.py`
Add one column to `Incident`:
```python
notes = db.Column(db.Text)
```
Existing relationships (`child`, `staff`, `interventions` m2m) are unchanged.

### 2. Demo seed — `config.py` + `app.py`
- `config.py`: set `SEED_DEMO_DATA = True`; add `DEMO_CHILDREN`, a list of ~4
  generic children (`Student A`–`D`), each with `room` drawn from `ROOMS`,
  varied `support`, and `key_worker` referencing a name from `STAFF`.
- `app.py` `seed_lookups()`: add a branch — if `config.SEED_DEMO_DATA` and
  `Child.query.count() == 0`, insert `DEMO_CHILDREN`, linking `key_worker` to
  the matching seeded `Staff` row by name. Staff is already seeded from
  `config.STAFF`.

### 3. Endpoint — `POST /api/incidents` (`app.py`)
Accepts JSON from the form:
`childId, date, time, type, severity, trigger, description, duration,
outcome, staff (name), notes, interventions[] (names)`.

Logic:
1. Validate required fields present (`childId, date, time, type, severity,
   description`) → `400` with message otherwise.
2. Validate `childId` exists → `400` if not.
3. Validate `type ∈ INCIDENT_TYPES` and `severity ∈ SEVERITY_LEVELS` → `400`
   if invalid (light validation against `config`).
4. Parse `date` + `time` into `occurred_at` (datetime) → `400` on parse error.
5. Resolve `staff` name → `Staff` row (or `None` if empty/unmatched).
6. Resolve `interventions[]` names → existing `Intervention` rows (seeded from
   config); unknown names are ignored.
7. Create `Incident` with `status='Resolved'`, commit.
8. Respond `201` with the incident serialized in the **same shape** as the
   dashboard route (`_serialize_incident`: `childId, date, time,
   interventions[] as names, staff as name`), so the frontend can append it to
   `INCIDENTS` directly.

### 4. Frontend — `templates/dashboard.html`
`saveIncident()` becomes `async`:
- Existing client-side validation runs first (child selected, description,
  severity).
- Build payload, `await fetch('/api/incidents', {method:'POST', headers:
  {'Content-Type':'application/json'}, body: JSON.stringify(payload)})`.
- On `res.ok`: `INCIDENTS.push(await res.json())`, reset form state,
  `showToast('Incident saved')`, `showTab('dashboard')`.
- On error: `alert` with the message from the response body.

### 5. Tests — `tests/test_incidents.py`
Pytest with a test app on SQLite (in-memory or temp file) and `SEED_DEMO_DATA`
controlled within the test. Cases:
- Valid POST → `201`; row exists in DB; `occurred_at` correct; `notes` saved;
  `staff` linked; `interventions` linked (m2m); `GET /api/incidents` returns it.
- Missing required field → `400`.
- Non-existent `childId` → `400`.
- Invalid `type` / `severity` → `400`.
- Unknown intervention name → ignored, the rest are saved.

## Data flow

```
Log Incident form (browser)
  → saveIncident() builds JSON payload
  → POST /api/incidents
  → validate → resolve staff/interventions → create Incident → commit
  → 201 + serialized incident
  → INCIDENTS.push(record) → re-render dashboard
```

## Error handling

- All validation failures return `400` with a human-readable `{"error": ...}`
  body; the frontend surfaces it via `alert`.
- Client-side guards (existing) prevent the most common empty submissions
  before the network call.

## Files touched

- `models.py` — add `notes` column.
- `config.py` — `SEED_DEMO_DATA = True`; add `DEMO_CHILDREN`.
- `app.py` — extend `seed_lookups()`; add `POST /api/incidents`.
- `templates/dashboard.html` — `saveIncident()` async fetch.
- `tests/test_incidents.py` — new.
- Delete `instance/behaviour.db` if present (new `notes` column; blank slate, no
  data to lose).

## Out of scope (future)

- Edit / delete incidents.
- Settings CRUD for children/staff/classes.
- Real PDF report generation.
- POST validation of `trigger`/`outcome` against config (kept lenient for now).
