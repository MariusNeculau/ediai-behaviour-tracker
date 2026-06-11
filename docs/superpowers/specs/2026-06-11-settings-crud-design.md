# Design: Settings CRUD (Students, Staff, Rooms)

**Date:** 2026-06-11
**Project:** EDI AI Behaviour Tracker (Local Desktop — Flask/SQLite)
**Status:** Approved (design phase)
**Roadmap:** Step 2 — make the app "presentable" and enterprise-ready for New
Frontiers by enabling dynamic management of students, staff, and classes.

## Goal

Replace the static, config-seeded lists of students/staff/classes with full
CRUD managed from the Settings tab. Administrators must be able to add, edit,
and remove students (including changing a student's `room` and `key worker`),
staff, and rooms — **without losing the incident history** of any student.

Scope is strictly the three entities **Students (Child), Staff, Rooms**. School
information and behaviour taxonomies (incident types, triggers, interventions,
etc.) stay config-driven and read-only for this step (YAGNI).

## Decisions

- **Deletion strategy: soft-delete (archive).** Every managed entity gets an
  `active` boolean. "Deleting" sets `active=False`; the row and all relations
  (especially a student's incidents) stay in the database. This gives an audit
  trail and is friendly to GDPR / record-retention obligations.
- **Rooms become a table.** `Room` is promoted from a plain string on `Child`
  (validated against `config.ROOMS`) to a first-class model with an FK
  (`Child.room_id`). Enables referential integrity, propagated renames, and
  blocking deletion of in-use rooms.
- **Referential integrity: block-when-in-use.** Archiving a `Staff` who is the
  key worker of any *active* child, or a `Room` that still holds *active*
  children, is refused with a clear, actionable message (HTTP `409`). The user
  must reassign first.
- **Incident history is protected** because we never hard-delete a child, and
  `Incident.child_id` stays `NOT NULL`. Changing a child's `room_id` or
  `key_worker_id` is a plain update and does not touch incidents.
- **No Alembic migration.** The app is a "blank slate", single-user local
  desktop tool and `instance/` is gitignored. As in Step 1, the dev database is
  recreated; `seed_lookups()` is updated for the new schema.
- **Code organization:** Settings endpoints live in a new Flask **Blueprint**
  (`settings_api.py`) registered under `/api`, keeping `app.py` thin
  (bootstrap + dashboard + incidents).
- **Tests:** TDD with pytest, reusing `tests/conftest.py`. Tests written before
  implementation.

## Components

### 1. Models — `models.py`

```python
class Room(db.Model):                 # NEW
    __tablename__ = "room"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    children = db.relationship("Child", back_populates="room")

class Child(db.Model):                 # MODIFIED
    # room (String) -> room_id (FK), NOT NULL
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    room = db.relationship("Room", back_populates="children")
    active = db.Column(db.Boolean, nullable=False, default=True)   # soft-delete
    # key_worker_id, incidents relationship unchanged

class Staff(db.Model):                 # MODIFIED
    active = db.Column(db.Boolean, nullable=False, default=True)   # soft-delete
```

- `Incident` is **unchanged**: `child_id` stays `NOT NULL`. The existing
  `cascade="all, delete-orphan"` on `Child.incidents` stays but is never
  triggered now (children are archived, not deleted).
- The current `Child.room` string column is replaced by `room_id`; any code
  referencing `c.room` (e.g. serialization, templates) now reads
  `c.room.name`.

### 2. Config & seed — `config.py` + `app.py`

- `config.ROOMS` stays as the seed source for the `Room` table.
- `seed_lookups()` gains a branch: if `Room.query.count() == 0`, insert a
  `Room` per name in `config.ROOMS`.
- `DEMO_CHILDREN` seeding resolves `room` name → seeded `Room` row and sets
  `room_id` (instead of the old string assignment).

### 3. Settings API — `settings_api.py` (NEW Blueprint, under `/api`)

All list endpoints return only `active=True` rows by default; `?all=1`
includes archived. All mutations return JSON; validation failures return `400`
with `{"error": ...}`; integrity conflicts return `409` with an actionable
message.

```
Rooms
  GET    /api/rooms
  POST   /api/rooms             {name}                         -> 201
  PUT    /api/rooms/<id>        {name}                         -> 200
  DELETE /api/rooms/<id>        soft-delete                    -> 200 | 409 in use

Staff
  GET    /api/staff
  POST   /api/staff            {name, role}                    -> 201
  PUT    /api/staff/<id>       {name, role}                    -> 200
  DELETE /api/staff/<id>       soft-delete                     -> 200 | 409 in use

Children
  GET    /api/children
  POST   /api/children         {name, roomId, age, support, keyWorkerId}  -> 201
  PUT    /api/children/<id>    {name, roomId, age, support, keyWorkerId}  -> 200
  DELETE /api/children/<id>    soft-delete                     -> 200
```

**Validation rules:**
- `name` required and non-empty. For Room/Staff, `name` is unique at the DB
  level across **all** rows (active or archived); a duplicate returns `400`.
  (Archived names are not recycled — acceptable for a school context.)
- `roomId` must reference an existing, active `Room`.
- `keyWorkerId` (optional) must reference an existing, active `Staff`.
- `support` must be in `config.SUPPORT_LEVELS`.
- `role` is free text (consistent with current behaviour).

**Integrity rules (return `409`):**
- `DELETE /api/staff/<id>` — refused if the staff member is the key worker of
  any active child. Message names the count: "Reassign N student(s) first."
- `DELETE /api/rooms/<id>` — refused if any active child has `room_id == id`.

### 4. Serialization — `app.py`

- `_serialize_child` is extended to return `roomId` and `keyWorkerId`
  (alongside the existing `room` and `keyWorker` *names*, kept for the current
  UI). `room` becomes `c.room.name`.
- Add `_serialize_room(r)` → `{id, name, active}` and `_serialize_staff(s)` →
  `{id, name, role, active}`.
- The dashboard route passes active rooms/staff/children to the template; the
  rooms list (formerly `config.ROOMS`) is now derived from the `Room` table.

### 5. Frontend — `templates/dashboard.html`

- `renderSettings()` rewrites the **Classes**, **Staff**, and a new
  **Students** section as tables with per-row **Edit / Archive** actions plus an
  **Add** button.
- Add/Edit open a modal (reuse the existing `overlay`/`modal` pattern) with a
  form; submit → `fetch` (POST/PUT) → on success update the in-memory array
  (`CHILDREN` / `STAFF` / `ROOMS`) and re-render — same pattern as
  `saveIncident()`.
- Archive → `DELETE`; on `409` show the integrity message via `alert`; on
  success remove from the active list.
- The class dropdown in the Log Incident / child forms is populated from the
  now-dynamic rooms list.
- School Information and Incident Types remain read-only (scope).

### 6. Tests — `tests/test_settings.py` (NEW) + `tests/conftest.py`

Reuse the temp-SQLite `app`/`client` fixtures; add a `room_id` fixture.

- **Rooms:** create / rename / list; duplicate name → 400; archive empty room →
  200; archive room with an active child → 409.
- **Staff:** create / edit / list; archive staff with no children → 200;
  archive staff who is an active key worker → 409.
- **Children:** create with valid `roomId`/`keyWorkerId` → 201; non-existent
  `roomId` → 400; **update `room_id` preserves the child's incidents** (the key
  test for the history requirement); archive child → absent from the active
  list but the child row and its incidents remain in the DB.

## Data flow (example: edit a student's class)

```
Settings > Students table > Edit
  -> modal form with current values
  -> PUT /api/children/<id> {roomId: newRoom, ...}
  -> validate roomId active -> update child.room_id -> commit
  -> 200 + serialized child
  -> update CHILDREN entry -> re-render (incidents untouched)
```

## Error handling

- Validation failures → `400` `{"error": ...}`; surfaced via `alert`.
- Integrity conflicts (archive in-use staff/room) → `409` with an actionable
  message naming what to reassign.
- DB commit failures → `500` `{"error": ...}` with rollback (as in the incident
  endpoint).

## Files touched

- `models.py` — add `Room`; `Child.room` → `room_id` + relationship; add
  `active` to `Child` and `Staff`.
- `config.py` — (no structural change; `ROOMS` stays as the Room seed source).
- `app.py` — seed `Room`; resolve `DEMO_CHILDREN.room` → `room_id`; extend
  serialization; register the settings blueprint.
- `settings_api.py` — NEW blueprint with the CRUD endpoints above.
- `templates/dashboard.html` — rewrite `renderSettings()` tables/modals; dynamic
  rooms.
- `tests/test_settings.py` — NEW.
- `tests/conftest.py` — add `room_id` fixture (and adjust `child_id` to use
  `room_id`).
- Delete `instance/behaviour.db` if present (schema change; blank slate).

## Out of scope (future)

- Editable taxonomies (incident types, triggers, interventions, outcomes).
- Editable School Information persisted to the DB.
- Authentication / roles / per-user access control.
- Alembic migrations.
- "Show archived" / restore-from-archive UI (data is retained in the DB; a
  toggle can be added later via the existing `?all=1` support).
