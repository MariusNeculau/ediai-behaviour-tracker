# Settings CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full CRUD for Students, Staff, and Classes (Rooms) from the Settings tab, with soft-delete (archive) so incident history is never lost when a student changes class or is removed.

**Architecture:** Flask + Flask-SQLAlchemy + SQLite. `Room` is promoted from a string on `Child` to its own table with an FK (`Child.room_id`). `Child` and `Staff` gain an `active` flag for soft-delete. CRUD endpoints live in a new Flask **Blueprint** (`settings_api.py`) under `/api`; JSON shapes live in a new `serializers.py` shared by `app.py` and the blueprint (avoids a circular import). The SPA frontend (`templates/dashboard.html`) gets table-based Settings sections with Add/Edit/Archive modals that call the endpoints with `fetch` and mutate the in-memory `CHILDREN`/`STAFF`/`ROOMS` arrays — the same pattern as the existing `saveIncident()`.

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, SQLite, pytest, vanilla JS (fetch).

---

## File Structure

- `models.py` (modify) — add `Room`; change `Child.room` → `room_id` + relationship; add `active` to `Child` and `Staff`.
- `serializers.py` (create) — `serialize_room`, `serialize_staff`, `serialize_child`.
- `app.py` (modify) — seed `Room`; resolve `DEMO_CHILDREN.room` → `room_id`; import serializers; dashboard passes active rooms/staff/children; register the settings blueprint.
- `settings_api.py` (create) — CRUD blueprint for Rooms, Staff, Children.
- `tests/conftest.py` (modify) — fix `child_id` fixture for `room_id`; add `room_id` and `staff_id` fixtures.
- `tests/test_settings.py` (create) — model + endpoint tests.
- `templates/dashboard.html` (modify) — add `ROOMS` global; rewrite `renderSettings()`; add entity modals + fetch handlers; replace `CONFIG.rooms` usages.
- `DEVELOPER_NOTES.md` (modify) — tick the Settings CRUD item.

---

## Task 1: Remove the stale dev database (schema change)

**Files:**
- (none — local DB cleanup only)

- [ ] **Step 1: Remove any stale DB (schema changes in Task 2)**

Run (PowerShell): `if (Test-Path instance/behaviour.db) { Remove-Item instance/behaviour.db -Force }`
Expected: no error. Blank slate, no data to lose (`instance/` is gitignored).

- [ ] **Step 2: Confirm the test suite is green before starting**

Run: `pytest -q`
Expected: all existing tests PASS (this is the baseline before changes).

---

## Task 2: Schema + serialization foundation

Promote `Room` to a table, add `active` flags, and route all entity JSON through a shared `serializers.py`. Keep the whole suite green by updating the seed, the dashboard, and the fixtures in the same task.

**Files:**
- Modify: `models.py` (the `Child` and `Staff` classes; add a `Room` class)
- Create: `serializers.py`
- Modify: `app.py` (imports; `seed_lookups`; dashboard route; remove old `_serialize_child`)
- Modify: `tests/conftest.py` (`child_id` fixture; add `room_id`, `staff_id`)
- Create: `tests/test_settings.py` (model + serializer tests)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_settings.py`:

```python
import config


def test_room_model_and_child_fk(app):
    from models import db, Child, Room

    with app.app_context():
        # Rooms are seeded from config.ROOMS by create_app()
        assert Room.query.count() == len(config.ROOMS)
        room = Room.query.filter_by(name="Room 1").first()
        assert room is not None and room.active is True

        c = Child(name="X", room_id=room.id, support="High")
        db.session.add(c)
        db.session.commit()

        got = db.session.get(Child, c.id)
        assert got.room.name == "Room 1"
        assert got.active is True


def test_serialize_child_includes_ids(app):
    from serializers import serialize_child
    from models import db, Child, Room, Staff

    with app.app_context():
        room = Room.query.filter_by(name="Room 1").first()
        kw = Staff.query.filter_by(name="Staff Member 1").first()
        c = Child(name="Z", room_id=room.id, key_worker_id=kw.id, support="Low")
        db.session.add(c)
        db.session.commit()

        out = serialize_child(c)
        assert out["roomId"] == room.id
        assert out["keyWorkerId"] == kw.id
        assert out["room"] == "Room 1"
        assert out["active"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_settings.py -v`
Expected: FAIL — `ImportError`/`AttributeError` (no `Room`, no `serializers`).

- [ ] **Step 3: Update `models.py`**

Add a `Room` class (place it above `Child`):

```python
class Room(db.Model):
    """Clasă / cameră — promovată din string pe Child la entitate proprie."""

    __tablename__ = "room"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    children = db.relationship("Child", back_populates="room")

    def __repr__(self):
        return f"<Room {self.id} {self.name!r}>"
```

In `Child`, replace the `room` string column:

```python
    room = db.Column(db.String(60), nullable=False)           # ex: "Room 1"
```

with:

```python
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
```

and add the relationship next to the existing `key_worker`/`incidents` relationships in `Child`:

```python
    room = db.relationship("Room", back_populates="children")
```

In `Staff`, add (next to its columns):

```python
    active = db.Column(db.Boolean, nullable=False, default=True)
```

- [ ] **Step 4: Create `serializers.py`**

```python
"""serializers.py — JSON shapes for the managed entities (Room, Staff, Child).

Kept in a dedicated module so both app.py (dashboard) and settings_api.py
(CRUD blueprint) import them without a circular import.
"""


def serialize_room(r):
    return {"id": r.id, "name": r.name, "active": r.active}


def serialize_staff(s):
    return {"id": s.id, "name": s.name, "role": s.role, "active": s.active}


def serialize_child(c):
    return {
        "id": c.id,
        "name": c.name,
        "room": c.room.name if c.room else "",
        "roomId": c.room_id,
        "age": c.age,
        "support": c.support,
        "keyWorker": c.key_worker.name if c.key_worker else "",
        "keyWorkerId": c.key_worker_id,
        "active": c.active,
    }
```

- [ ] **Step 5: Update `app.py` — imports**

Change the models import line:

```python
from models import db, Child, Staff, Incident, Intervention
```

to:

```python
from models import db, Child, Staff, Room, Incident, Intervention
from serializers import serialize_child, serialize_staff, serialize_room
```

- [ ] **Step 6: Update `app.py` — remove the old `_serialize_child`**

Delete the entire `_serialize_child` function (the `def _serialize_child(c): ... }` block near the top). `_serialize_incident` stays.

- [ ] **Step 7: Update `app.py` — `seed_lookups()`**

At the start of `seed_lookups()` (before the `Intervention` block), add Room seeding:

```python
    if Room.query.count() == 0:
        for name in config.ROOMS:
            db.session.add(Room(name=name))
        db.session.commit()
```

Replace the `DEMO_CHILDREN` block with one that resolves `room_id`:

```python
    if config.SEED_DEMO_DATA and Child.query.count() == 0:
        staff_by_name = {s.name: s for s in Staff.query.all()}
        room_by_name = {r.name: r for r in Room.query.all()}
        for d in config.DEMO_CHILDREN:
            room = room_by_name.get(d["room"])
            db.session.add(
                Child(
                    name=d["name"],
                    room_id=room.id if room else None,
                    age=d.get("age"),
                    support=d.get("support"),
                    key_worker=staff_by_name.get(d.get("keyWorker")),
                )
            )
        db.session.commit()
```

- [ ] **Step 8: Update `app.py` — dashboard route data**

In the `dashboard()` route's `render_template(...)` call, replace the `children=` and `staff=` lines and add a `rooms=` line:

```python
            children=[serialize_child(c) for c in Child.query.filter_by(active=True).all()],
            staff=[serialize_staff(s) for s in Staff.query.filter_by(active=True).all()],
            rooms=[serialize_room(r) for r in Room.query.filter_by(active=True).all()],
```

(Leave the `incidents=[_serialize_incident(i) ...]` line unchanged.)

- [ ] **Step 9: Update `tests/conftest.py`**

Replace the `child_id` fixture body and add two fixtures:

```python
@pytest.fixture
def child_id(app):
    """Create one child (in a seeded room) and return its id."""
    from models import db, Child, Room

    with app.app_context():
        room = Room.query.filter_by(name="Room 1").first()
        c = Child(name="Test Child", room_id=room.id, age=8, support="High")
        db.session.add(c)
        db.session.commit()
        return c.id


@pytest.fixture
def room_id(app):
    from models import Room

    with app.app_context():
        return Room.query.filter_by(name="Room 1").first().id


@pytest.fixture
def staff_id(app):
    from models import Staff

    with app.app_context():
        return Staff.query.filter_by(name="Staff Member 1").first().id
```

- [ ] **Step 10: Run the full suite**

Run: `pytest -q`
Expected: all PASS — the new model/serializer tests plus the existing incident tests (which use the updated `child_id` fixture and the new `room_id`-based seed).

- [ ] **Step 11: Commit**

```bash
git add models.py serializers.py app.py tests/conftest.py tests/test_settings.py
git commit -m "feat: promote Room to a table and add soft-delete flags

Add Room model + Child.room_id FK, active flags on Child/Staff, and a
shared serializers module. Seed rooms from config; wire the dashboard to
serve active-only rows."
```

---

## Task 3: Rooms CRUD API (blueprint + registration)

**Files:**
- Create: `settings_api.py`
- Modify: `app.py` (`create_app` — register the blueprint)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_settings.py`:

```python
def test_create_and_list_room(client):
    res = client.post("/api/rooms", json={"name": "Room X"})
    assert res.status_code == 201
    assert res.get_json()["name"] == "Room X"
    names = [r["name"] for r in client.get("/api/rooms").get_json()]
    assert "Room X" in names


def test_create_room_duplicate_returns_400(client):
    client.post("/api/rooms", json={"name": "Dup"})
    res = client.post("/api/rooms", json={"name": "Dup"})
    assert res.status_code == 400


def test_create_room_blank_returns_400(client):
    res = client.post("/api/rooms", json={"name": "   "})
    assert res.status_code == 400


def test_rename_room(client):
    rid = client.post("/api/rooms", json={"name": "Old"}).get_json()["id"]
    res = client.put(f"/api/rooms/{rid}", json={"name": "New"})
    assert res.status_code == 200
    assert res.get_json()["name"] == "New"


def test_archive_empty_room(client):
    rid = client.post("/api/rooms", json={"name": "Empty"}).get_json()["id"]
    res = client.delete(f"/api/rooms/{rid}")
    assert res.status_code == 200
    names = [r["name"] for r in client.get("/api/rooms").get_json()]
    assert "Empty" not in names


def test_archive_room_in_use_returns_409(app, client, room_id):
    from models import db, Child

    with app.app_context():
        db.session.add(Child(name="Kid", room_id=room_id, support="High"))
        db.session.commit()
    res = client.delete(f"/api/rooms/{room_id}")
    assert res.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_settings.py -k room -v`
Expected: FAIL — `404 Not Found` (no `/api/rooms` route yet).

- [ ] **Step 3: Create `settings_api.py` with the Rooms endpoints**

```python
"""settings_api.py — CRUD blueprint for the managed entities.

Registered under /api by app.create_app(). Covers Rooms, Staff, and Children.
Deletion is soft (active=False). Archiving an entity that is still in use
(a Room with active children, or a Staff who is an active key worker) is
refused with HTTP 409 and an actionable message.
"""

from flask import Blueprint, jsonify, request

import config
from models import db, Child, Staff, Room
from serializers import serialize_room, serialize_staff, serialize_child

settings_bp = Blueprint("settings", __name__, url_prefix="/api")


# ─── Rooms ──────────────────────────────────────────────────────────────────

@settings_bp.route("/rooms", methods=["GET"])
def list_rooms():
    q = Room.query if request.args.get("all") else Room.query.filter_by(active=True)
    return jsonify([serialize_room(r) for r in q.order_by(Room.name).all()])


@settings_bp.route("/rooms", methods=["POST"])
def create_room():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if Room.query.filter_by(name=name).first():
        return jsonify({"error": "A class with that name already exists"}), 400
    room = Room(name=name)
    db.session.add(room)
    db.session.commit()
    return jsonify(serialize_room(room)), 201


@settings_bp.route("/rooms/<int:room_id>", methods=["PUT"])
def update_room(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Unknown room"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if Room.query.filter(Room.name == name, Room.id != room_id).first():
        return jsonify({"error": "A class with that name already exists"}), 400
    room.name = name
    db.session.commit()
    return jsonify(serialize_room(room))


@settings_bp.route("/rooms/<int:room_id>", methods=["DELETE"])
def delete_room(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Unknown room"}), 404
    in_use = Child.query.filter_by(room_id=room_id, active=True).count()
    if in_use:
        return jsonify({"error": f"Reassign {in_use} student(s) to another class first"}), 409
    room.active = False
    db.session.commit()
    return jsonify(serialize_room(room))
```

- [ ] **Step 4: Register the blueprint in `app.py`**

In `create_app()`, after the `register_routes(app)` line and before `return app`, add:

```python
    from settings_api import settings_bp
    app.register_blueprint(settings_bp)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_settings.py -k room -v`
Expected: all room tests PASS.

- [ ] **Step 6: Commit**

```bash
git add settings_api.py app.py tests/test_settings.py
git commit -m "feat: add Rooms CRUD API with soft-delete and in-use guard"
```

---

## Task 4: Staff CRUD API

**Files:**
- Modify: `settings_api.py` (append Staff endpoints)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_settings.py`:

```python
def test_create_and_list_staff(client):
    res = client.post("/api/staff", json={"name": "New Teacher", "role": "Teacher"})
    assert res.status_code == 201
    names = [s["name"] for s in client.get("/api/staff").get_json()]
    assert "New Teacher" in names


def test_create_staff_duplicate_returns_400(client):
    # "Staff Member 1" is seeded from config
    res = client.post("/api/staff", json={"name": "Staff Member 1"})
    assert res.status_code == 400


def test_edit_staff(client):
    sid = client.post("/api/staff", json={"name": "Temp"}).get_json()["id"]
    res = client.put(f"/api/staff/{sid}", json={"name": "Temp", "role": "SNA"})
    assert res.status_code == 200
    assert res.get_json()["role"] == "SNA"


def test_archive_staff_without_children(client):
    sid = client.post("/api/staff", json={"name": "Lonely"}).get_json()["id"]
    res = client.delete(f"/api/staff/{sid}")
    assert res.status_code == 200


def test_archive_staff_keyworker_returns_409(app, client, room_id, staff_id):
    from models import db, Child

    with app.app_context():
        db.session.add(
            Child(name="Kid", room_id=room_id, support="High", key_worker_id=staff_id)
        )
        db.session.commit()
    res = client.delete(f"/api/staff/{staff_id}")
    assert res.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_settings.py -k staff -v`
Expected: FAIL — `404 Not Found` (no `/api/staff` POST/PUT/DELETE yet).

- [ ] **Step 3: Append the Staff endpoints to `settings_api.py`**

Add after the Rooms section:

```python
# ─── Staff ──────────────────────────────────────────────────────────────────

@settings_bp.route("/staff", methods=["GET"])
def list_staff():
    q = Staff.query if request.args.get("all") else Staff.query.filter_by(active=True)
    return jsonify([serialize_staff(s) for s in q.order_by(Staff.name).all()])


@settings_bp.route("/staff", methods=["POST"])
def create_staff():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if Staff.query.filter_by(name=name).first():
        return jsonify({"error": "A staff member with that name already exists"}), 400
    member = Staff(name=name, role=(data.get("role") or "").strip() or None)
    db.session.add(member)
    db.session.commit()
    return jsonify(serialize_staff(member)), 201


@settings_bp.route("/staff/<int:staff_id>", methods=["PUT"])
def update_staff(staff_id):
    member = db.session.get(Staff, staff_id)
    if member is None:
        return jsonify({"error": "Unknown staff member"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if Staff.query.filter(Staff.name == name, Staff.id != staff_id).first():
        return jsonify({"error": "A staff member with that name already exists"}), 400
    member.name = name
    member.role = (data.get("role") or "").strip() or None
    db.session.commit()
    return jsonify(serialize_staff(member))


@settings_bp.route("/staff/<int:staff_id>", methods=["DELETE"])
def delete_staff(staff_id):
    member = db.session.get(Staff, staff_id)
    if member is None:
        return jsonify({"error": "Unknown staff member"}), 404
    in_use = Child.query.filter_by(key_worker_id=staff_id, active=True).count()
    if in_use:
        return jsonify({"error": f"Reassign {in_use} student(s) to another key worker first"}), 409
    member.active = False
    db.session.commit()
    return jsonify(serialize_staff(member))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_settings.py -k staff -v`
Expected: all staff tests PASS.

- [ ] **Step 5: Commit**

```bash
git add settings_api.py tests/test_settings.py
git commit -m "feat: add Staff CRUD API with key-worker in-use guard"
```

---

## Task 5: Children CRUD API (history preservation)

**Files:**
- Modify: `settings_api.py` (append Children endpoints + payload resolver)
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_settings.py`:

```python
def test_create_child_valid(client, room_id, staff_id):
    res = client.post(
        "/api/children",
        json={"name": "Alice", "roomId": room_id, "age": 7, "support": "High", "keyWorkerId": staff_id},
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["roomId"] == room_id
    assert body["keyWorkerId"] == staff_id
    assert body["name"] == "Alice"


def test_create_child_unknown_room_returns_400(client):
    res = client.post("/api/children", json={"name": "Bob", "roomId": 99999})
    assert res.status_code == 400


def test_create_child_blank_name_returns_400(client, room_id):
    res = client.post("/api/children", json={"name": "", "roomId": room_id})
    assert res.status_code == 400


def test_update_child_room_preserves_incidents(app, client, child_id):
    from models import db, Incident, Room
    from datetime import datetime

    with app.app_context():
        db.session.add(
            Incident(child_id=child_id, occurred_at=datetime(2026, 6, 11, 9, 30), type="Crisis", severity="High")
        )
        db.session.commit()
        other_room = Room.query.filter_by(name="Room 2").first().id

    res = client.put(f"/api/children/{child_id}", json={"name": "Test Child", "roomId": other_room})
    assert res.status_code == 200
    assert res.get_json()["roomId"] == other_room

    with app.app_context():
        assert Incident.query.filter_by(child_id=child_id).count() == 1


def test_archive_child_keeps_row_and_incidents(app, client, child_id):
    from models import db, Child, Incident
    from datetime import datetime

    with app.app_context():
        db.session.add(
            Incident(child_id=child_id, occurred_at=datetime(2026, 6, 11, 9, 30), type="Crisis", severity="High")
        )
        db.session.commit()

    res = client.delete(f"/api/children/{child_id}")
    assert res.status_code == 200

    active = client.get("/api/children").get_json()
    assert all(c["id"] != child_id for c in active)
    archived = client.get("/api/children?all=1").get_json()
    assert any(c["id"] == child_id for c in archived)

    with app.app_context():
        assert db.session.get(Child, child_id) is not None
        assert Incident.query.filter_by(child_id=child_id).count() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_settings.py -k child -v`
Expected: FAIL — `404 Not Found` (no `/api/children` write routes yet).

- [ ] **Step 3: Append the Children endpoints to `settings_api.py`**

Add after the Staff section:

```python
# ─── Children ───────────────────────────────────────────────────────────────

def _resolve_child_payload(data):
    """Validate a child payload. Returns (fields, error, status)."""
    name = (data.get("name") or "").strip()
    if not name:
        return None, "Name is required", 400

    room_id = data.get("roomId")
    room = db.session.get(Room, room_id) if room_id else None
    if room is None or not room.active:
        return None, "A valid class is required", 400

    key_worker_id = data.get("keyWorkerId") or None
    if key_worker_id:
        kw = db.session.get(Staff, key_worker_id)
        if kw is None or not kw.active:
            return None, "Unknown key worker", 400

    support = data.get("support")
    if support and support not in config.SUPPORT_LEVELS:
        return None, "Invalid support level", 400

    fields = {
        "name": name,
        "room_id": room.id,
        "key_worker_id": key_worker_id,
        "age": data.get("age"),
        "support": support,
    }
    return fields, None, None


@settings_bp.route("/children", methods=["GET"])
def list_children():
    q = Child.query if request.args.get("all") else Child.query.filter_by(active=True)
    return jsonify([serialize_child(c) for c in q.order_by(Child.name).all()])


@settings_bp.route("/children", methods=["POST"])
def create_child():
    data = request.get_json(silent=True) or {}
    fields, error, status = _resolve_child_payload(data)
    if error:
        return jsonify({"error": error}), status
    child = Child(**fields)
    db.session.add(child)
    db.session.commit()
    return jsonify(serialize_child(child)), 201


@settings_bp.route("/children/<int:child_id>", methods=["PUT"])
def update_child(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404
    data = request.get_json(silent=True) or {}
    fields, error, status = _resolve_child_payload(data)
    if error:
        return jsonify({"error": error}), status
    for key, value in fields.items():
        setattr(child, key, value)
    db.session.commit()
    return jsonify(serialize_child(child))


@settings_bp.route("/children/<int:child_id>", methods=["DELETE"])
def delete_child(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404
    child.active = False
    db.session.commit()
    return jsonify(serialize_child(child))
```

- [ ] **Step 4: Run the full suite to verify everything passes**

Run: `pytest -q`
Expected: all PASS (incident tests + all room/staff/child tests).

- [ ] **Step 5: Commit**

```bash
git add settings_api.py tests/test_settings.py
git commit -m "feat: add Children CRUD API; soft-delete preserves incidents"
```

---

## Task 6: Frontend — Settings tables, modals, dynamic rooms

This task is verified by template-render (pytest) plus a manual browser pass; the JS is not unit-tested.

**Files:**
- Modify: `templates/dashboard.html`

- [ ] **Step 1: Add the `ROOMS` global**

Find the line:

```javascript
const STAFF     = {{ staff | tojson }};
```

Add immediately after it:

```javascript
const ROOMS     = {{ rooms | tojson }};
```

- [ ] **Step 2: Replace `CONFIG.rooms` in the profile filter**

In `renderProfiles()`, find:

```javascript
  const rooms=['All Rooms', ...CONFIG.rooms];
```

Replace with:

```javascript
  const rooms=['All Rooms', ...ROOMS.map(r=>r.name)];
```

- [ ] **Step 3: Replace `renderSettings()` entirely**

Find the existing `function renderSettings(){ ... }` and replace the whole function with:

```javascript
function renderSettings(){
  const studentRows=CHILDREN.map(c=>`<div class="set-row">
    <div><div class="set-name">${c.name}</div><div class="set-role">${c.room} &middot; ${c.keyWorker||'No key worker'}${c.age?(' &middot; Age '+c.age):''}</div></div>
    <div style="display:flex;gap:8px">
      <button class="btn-outline" style="font-size:12px;padding:6px 12px" onclick="openChildModal(${c.id})">Edit</button>
      <button class="btn-outline" style="font-size:12px;padding:6px 12px" onclick="archiveChild(${c.id})">Archive</button>
    </div>
  </div>`).join('')||'<div style="color:var(--gray-500);font-size:13px">No students yet</div>';

  const roomRows=ROOMS.map(r=>`<div class="set-row">
    <div><div class="set-name">&#127979; ${r.name}</div></div>
    <div style="display:flex;gap:8px">
      <button class="btn-outline" style="font-size:12px;padding:6px 12px" onclick="openRoomModal(${r.id})">Edit</button>
      <button class="btn-outline" style="font-size:12px;padding:6px 12px" onclick="archiveRoom(${r.id})">Archive</button>
    </div>
  </div>`).join('')||'<div style="color:var(--gray-500);font-size:13px">No classes yet</div>';

  const staffRows=STAFF.map(s=>`<div class="set-row">
    <div><div class="set-name">${s.name}</div><div class="set-role">${s.role||'Staff'}</div></div>
    <div style="display:flex;gap:8px">
      <button class="btn-outline" style="font-size:12px;padding:6px 12px" onclick="openStaffModal(${s.id})">Edit</button>
      <button class="btn-outline" style="font-size:12px;padding:6px 12px" onclick="archiveStaff(${s.id})">Archive</button>
    </div>
  </div>`).join('')||'<div style="color:var(--gray-500);font-size:13px">No staff configured</div>';

  const typeTags=CONFIG.incident_types.map(t=>`<span class="tag">${t}</span>`).join('');

  return `
  <div style="max-width:720px">
    <div class="settings-section">
      <h3>&#128104; Students</h3>
      ${studentRows}
      <div style="margin-top:12px"><button class="btn-outline" onclick="openChildModal(null)">&#43; Add Student</button></div>
    </div>
    <div class="settings-section">
      <h3>&#127979; Classes</h3>
      ${roomRows}
      <div style="margin-top:12px"><button class="btn-outline" onclick="openRoomModal(null)">&#43; Add Class</button></div>
    </div>
    <div class="settings-section">
      <h3>&#128104; Staff Members</h3>
      ${staffRows}
      <div style="margin-top:12px"><button class="btn-outline" onclick="openStaffModal(null)">&#43; Add Staff Member</button></div>
    </div>
    <div class="settings-section">
      <h3>&#128221; Incident Types</h3>
      <div style="margin-bottom:12px">${typeTags}</div>
      <div style="color:var(--gray-500);font-size:12px">Configured in config.py</div>
    </div>
    <div class="settings-section">
      <h3>&#128274; GDPR &amp; Data Privacy</h3>
      <div class="gdpr">
        <div style="font-size:20px">&#128274;</div>
        <div><strong>Data stored locally only.</strong> All incident data is stored on your school's own system. No personal data is transmitted to external servers. This tool is fully compliant with GDPR and the Irish Data Protection Act 2018. All records are accessible only to authorised staff.</div>
      </div>
    </div>
  </div>`;
}
```

- [ ] **Step 4: Add the entity modal + handler functions**

Add the following block immediately after the `renderSettings()` function:

```javascript
// ─── SETTINGS CRUD ──────────────────────────────────────────────────────────
function openRoomModal(id){
  const r=id?ROOMS.find(x=>x.id===id):null;
  const overlay=document.getElementById('overlay');
  overlay.style.display='flex';overlay.className='overlay';
  overlay.innerHTML=`<div class="modal">
    <div class="modal-hdr"><div class="modal-title">${r?'Edit Class':'Add Class'}</div>
      <button class="modal-close" onclick="closeOverlay()">&#10005;</button></div>
    <div class="form-group"><label>Class Name</label>
      <input type="text" id="m-room-name" value="${r?r.name:''}"></div>
    <div style="margin-top:18px;display:flex;gap:10px">
      <button class="btn-outline" onclick="closeOverlay()">Cancel</button>
      <button class="btn-primary" style="width:auto;padding:10px 24px" onclick="saveRoom(${r?r.id:'null'})">Save</button>
    </div></div>`;
  overlay.onclick=function(e){if(e.target===overlay) closeOverlay();};
}
async function saveRoom(id){
  const name=document.getElementById('m-room-name').value.trim();
  if(!name){alert('Please enter a class name.');return;}
  const url=id?`/api/rooms/${id}`:'/api/rooms';const method=id?'PUT':'POST';
  try{
    const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    if(!res.ok){const e=await res.json().catch(()=>({}));alert(e.error||('HTTP '+res.status));return;}
    const saved=await res.json();
    if(id){const i=ROOMS.findIndex(x=>x.id===id);if(i>=0)ROOMS[i]=saved;}else ROOMS.push(saved);
    closeOverlay();showToast('Class saved');showTab('settings');
  }catch(err){alert('Network error: '+err.message);}
}
async function archiveRoom(id){
  if(!confirm('Archive this class? It will be hidden from active lists.'))return;
  try{
    const res=await fetch(`/api/rooms/${id}`,{method:'DELETE'});
    if(!res.ok){const e=await res.json().catch(()=>({}));alert(e.error||('HTTP '+res.status));return;}
    const i=ROOMS.findIndex(x=>x.id===id);if(i>=0)ROOMS.splice(i,1);
    showToast('Class archived');showTab('settings');
  }catch(err){alert('Network error: '+err.message);}
}

function openStaffModal(id){
  const s=id?STAFF.find(x=>x.id===id):null;
  const overlay=document.getElementById('overlay');
  overlay.style.display='flex';overlay.className='overlay';
  overlay.innerHTML=`<div class="modal">
    <div class="modal-hdr"><div class="modal-title">${s?'Edit Staff Member':'Add Staff Member'}</div>
      <button class="modal-close" onclick="closeOverlay()">&#10005;</button></div>
    <div class="form-group"><label>Name</label><input type="text" id="m-staff-name" value="${s?s.name:''}"></div>
    <div class="form-group"><label>Role</label><input type="text" id="m-staff-role" value="${s&&s.role?s.role:''}"></div>
    <div style="margin-top:18px;display:flex;gap:10px">
      <button class="btn-outline" onclick="closeOverlay()">Cancel</button>
      <button class="btn-primary" style="width:auto;padding:10px 24px" onclick="saveStaff(${s?s.id:'null'})">Save</button>
    </div></div>`;
  overlay.onclick=function(e){if(e.target===overlay) closeOverlay();};
}
async function saveStaff(id){
  const name=document.getElementById('m-staff-name').value.trim();
  const role=document.getElementById('m-staff-role').value.trim();
  if(!name){alert('Please enter a name.');return;}
  const url=id?`/api/staff/${id}`:'/api/staff';const method=id?'PUT':'POST';
  try{
    const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify({name,role})});
    if(!res.ok){const e=await res.json().catch(()=>({}));alert(e.error||('HTTP '+res.status));return;}
    const saved=await res.json();
    if(id){const i=STAFF.findIndex(x=>x.id===id);if(i>=0)STAFF[i]=saved;}else STAFF.push(saved);
    closeOverlay();showToast('Staff member saved');showTab('settings');
  }catch(err){alert('Network error: '+err.message);}
}
async function archiveStaff(id){
  if(!confirm('Archive this staff member?'))return;
  try{
    const res=await fetch(`/api/staff/${id}`,{method:'DELETE'});
    if(!res.ok){const e=await res.json().catch(()=>({}));alert(e.error||('HTTP '+res.status));return;}
    const i=STAFF.findIndex(x=>x.id===id);if(i>=0)STAFF.splice(i,1);
    showToast('Staff archived');showTab('settings');
  }catch(err){alert('Network error: '+err.message);}
}

function openChildModal(id){
  const c=id?CHILDREN.find(x=>x.id===id):null;
  const roomOpts=ROOMS.map(r=>`<option value="${r.id}"${c&&c.roomId===r.id?' selected':''}>${r.name}</option>`).join('');
  const staffOpts=`<option value="">&mdash; None &mdash;</option>`+STAFF.map(s=>`<option value="${s.id}"${c&&c.keyWorkerId===s.id?' selected':''}>${s.name}</option>`).join('');
  const supOpts=CONFIG.support_levels.map(l=>`<option${c&&c.support===l?' selected':''}>${l}</option>`).join('');
  const overlay=document.getElementById('overlay');
  overlay.style.display='flex';overlay.className='overlay';
  overlay.innerHTML=`<div class="modal">
    <div class="modal-hdr"><div class="modal-title">${c?'Edit Student':'Add Student'}</div>
      <button class="modal-close" onclick="closeOverlay()">&#10005;</button></div>
    <div class="form-group"><label>Name</label><input type="text" id="m-child-name" value="${c?c.name:''}"></div>
    <div class="form-group"><label>Class</label><select id="m-child-room">${roomOpts}</select></div>
    <div class="form-group"><label>Key Worker</label><select id="m-child-kw">${staffOpts}</select></div>
    <div class="form-group"><label>Age</label><input type="number" id="m-child-age" value="${c&&c.age?c.age:''}"></div>
    <div class="form-group"><label>Support Level</label><select id="m-child-support">${supOpts}</select></div>
    <div style="margin-top:18px;display:flex;gap:10px">
      <button class="btn-outline" onclick="closeOverlay()">Cancel</button>
      <button class="btn-primary" style="width:auto;padding:10px 24px" onclick="saveChild(${c?c.id:'null'})">Save</button>
    </div></div>`;
  overlay.onclick=function(e){if(e.target===overlay) closeOverlay();};
}
async function saveChild(id){
  const name=document.getElementById('m-child-name').value.trim();
  const roomId=parseInt(document.getElementById('m-child-room').value)||null;
  const kwVal=document.getElementById('m-child-kw').value;
  const keyWorkerId=kwVal?parseInt(kwVal):null;
  const ageVal=document.getElementById('m-child-age').value;
  const age=ageVal?parseInt(ageVal):null;
  const support=document.getElementById('m-child-support').value;
  if(!name){alert('Please enter a name.');return;}
  if(!roomId){alert('Please select a class.');return;}
  const payload={name,roomId,keyWorkerId,age,support};
  const url=id?`/api/children/${id}`:'/api/children';const method=id?'PUT':'POST';
  try{
    const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!res.ok){const e=await res.json().catch(()=>({}));alert(e.error||('HTTP '+res.status));return;}
    const saved=await res.json();
    if(id){const i=CHILDREN.findIndex(x=>x.id===id);if(i>=0)CHILDREN[i]=saved;}else CHILDREN.push(saved);
    closeOverlay();showToast('Student saved');showTab('settings');
  }catch(err){alert('Network error: '+err.message);}
}
async function archiveChild(id){
  if(!confirm('Archive this student? Their incident history is preserved.'))return;
  try{
    const res=await fetch(`/api/children/${id}`,{method:'DELETE'});
    if(!res.ok){const e=await res.json().catch(()=>({}));alert(e.error||('HTTP '+res.status));return;}
    const i=CHILDREN.findIndex(x=>x.id===id);if(i>=0)CHILDREN.splice(i,1);
    showToast('Student archived');showTab('settings');
  }catch(err){alert('Network error: '+err.message);}
}
```

- [ ] **Step 5: Verify the template still renders (no Jinja/JS breakage)**

Run: `pytest tests/test_settings.py::test_room_model_and_child_fk -v` and `pytest tests/test_incidents.py::test_dashboard_renders -v`
Expected: both PASS (the dashboard template compiles and renders 200 with the new `rooms` kwarg).

- [ ] **Step 6: Manual browser check**

Run: `python app.py` (then open http://127.0.0.1:5000/) and go to **Settings**.
Do, in order:
1. **Add Class** "Room 6" → appears in Classes; **Edit** it to "Room 6A" → name updates.
2. **Add Staff Member** "Test Teacher" / role "Teacher" → appears; **Edit** role → updates.
3. **Add Student** with a class + key worker → appears under Students; it also shows in **Child Profiles** and in the **Log Incident** child dropdown.
4. **Edit** that student's class → the class shown updates.
5. **Archive** an empty class → disappears. Try to archive a class that still has students → red `alert` "Reassign N student(s)…".
6. **Archive** the test student → disappears from Students; previously logged incidents for them remain in the dashboard list.

Expected: each action shows a green toast and the list updates without a full reload; integrity blocks show the server message. Stop the server with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: Settings CRUD UI for students, staff and classes"
```

---

## Task 7: Update developer notes

**Files:**
- Modify: `DEVELOPER_NOTES.md` (the "Task-uri rămase (post-pas 5)" section)

- [ ] **Step 1: Tick the Settings CRUD item**

Change the line:

```
- CRUD pentru elevi/staff/clase din ecranul Settings (acum read-only).
```

to:

```
- [x] CRUD elevi/staff/clase din Settings: soft-delete (arhivare), Room ca tabel cu FK, integritate referențială (blocare la arhivare în uz). Istoricul incidentelor păstrat la schimbarea clasei.
```

- [ ] **Step 2: Commit**

```bash
git add DEVELOPER_NOTES.md
git commit -m "docs: mark Settings CRUD done in developer notes"
```

---

## Done criteria

- `pytest -q` is green (existing incident tests + the new room/staff/child tests).
- In the browser: students, staff, and classes can be added/edited/archived from Settings; changes appear without a full reload.
- Archiving a class with active students, or a staff member who is an active key worker, is blocked with a clear message.
- Changing a student's class (or archiving the student) preserves their incident history in the database.
- No real school data introduced; demo entities remain generic.
```