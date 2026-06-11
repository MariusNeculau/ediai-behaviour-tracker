# Incident Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Log Incident form persist to SQLite via a create-only `POST /api/incidents`, with the server returning the saved record so the frontend can update its in-memory list (Approach A).

**Architecture:** Flask + Flask-SQLAlchemy backend, SQLite at `instance/behaviour.db`. A new POST route validates the form payload, resolves staff (by name) and interventions (by name), and creates an `Incident`. The SPA frontend (`templates/dashboard.html`) calls the endpoint with `fetch` and appends the returned record to `INCIDENTS`. Generic demo children are seeded so the form is usable before Settings CRUD exists.

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, SQLite, pytest, vanilla JS (fetch).

---

## File Structure

- `requirements.txt` (create) — runtime deps.
- `requirements-dev.txt` (create) — pytest.
- `tests/conftest.py` (create) — pytest fixtures for an isolated test app/client.
- `tests/test_incidents.py` (create) — endpoint + persistence tests.
- `models.py` (modify) — add `notes` column to `Incident`.
- `config.py` (modify) — `SEED_DEMO_DATA = True`; add `DEMO_CHILDREN`.
- `app.py` (modify) — seed demo children; add `notes` to `_serialize_incident`; add `POST /api/incidents`; make `api_incidents` reuse `_serialize_incident`.
- `templates/dashboard.html` (modify) — `saveIncident()` becomes async fetch.
- `DEVELOPER_NOTES.md` (modify) — tick the persistence follow-up.

---

## Task 1: Dev setup (dependencies + clean stale DB)

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create `requirements.txt`**

```
Flask>=3.0
Flask-SQLAlchemy>=3.1
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0
```

- [ ] **Step 3: Install dev dependencies**

Run: `pip install -r requirements-dev.txt`
Expected: Flask, Flask-SQLAlchemy, pytest installed (or "already satisfied").

- [ ] **Step 4: Remove any stale DB (the `notes` column is added in Task 3)**

Run (PowerShell): `if (Test-Path instance/behaviour.db) { Remove-Item instance/behaviour.db -Force }`
Expected: no error. Blank slate, no data to lose.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt requirements-dev.txt
git commit -m "chore: add requirements and dev requirements"
```

---

## Task 2: Test scaffolding (pytest fixtures + smoke test)

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_incidents.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    """A fresh Flask app bound to an isolated temp SQLite file.

    SEED_DEMO_DATA is forced off so tests control their own data.
    Lookups (Staff, Intervention) are still seeded from config by create_app().
    """
    import config

    db_file = tmp_path / "test.db"
    monkeypatch.setattr(config, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{db_file}")
    monkeypatch.setattr(config, "SEED_DEMO_DATA", False)

    import app as app_module

    application = app_module.create_app()
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def child_id(app):
    """Create one child and return its id."""
    from models import db, Child

    with app.app_context():
        c = Child(name="Test Child", room="Room 1", age=8, support="High")
        db.session.add(c)
        db.session.commit()
        return c.id
```

- [ ] **Step 2: Create `tests/test_incidents.py` with a smoke test**

```python
def test_dashboard_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Saplings" not in res.data
```

- [ ] **Step 3: Run the smoke test**

Run: `pytest tests/test_incidents.py::test_dashboard_renders -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_incidents.py
git commit -m "test: add pytest scaffolding and dashboard smoke test"
```

---

## Task 3: Add `notes` column to the Incident model

**Files:**
- Modify: `models.py` (the `Incident` class, after the `status` column ~line with `status = db.Column(...)`)
- Modify: `app.py:36-52` (`_serialize_incident`)
- Test: `tests/test_incidents.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_incidents.py`:

```python
def test_incident_has_notes_column(app, child_id):
    from models import db, Incident
    from datetime import datetime

    with app.app_context():
        inc = Incident(
            child_id=child_id,
            occurred_at=datetime(2026, 6, 11, 9, 30),
            type="Crisis",
            severity="High",
            notes="Parent contacted",
        )
        db.session.add(inc)
        db.session.commit()
        fetched = db.session.get(Incident, inc.id)
        assert fetched.notes == "Parent contacted"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_incidents.py::test_incident_has_notes_column -v`
Expected: FAIL — `TypeError: 'notes' is an invalid keyword argument for Incident`.

- [ ] **Step 3: Add the column**

In `models.py`, inside the `Incident` class, add immediately after the `status` column:

```python
    notes = db.Column(db.Text)
```

- [ ] **Step 4: Add `notes` to the serializer**

In `app.py`, in `_serialize_incident`, add a `"notes"` key (after `"status"`):

```python
        "status": i.status,
        "notes": i.notes,
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_incidents.py::test_incident_has_notes_column -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add models.py app.py tests/test_incidents.py
git commit -m "feat: add notes column to Incident model"
```

---

## Task 4: Seed generic demo children

**Files:**
- Modify: `config.py` (the `SEED_DEMO_DATA` line near the bottom; add `DEMO_CHILDREN`)
- Modify: `app.py:86-96` (`seed_lookups`)
- Test: `tests/test_incidents.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_incidents.py`:

```python
def test_demo_children_seeded_when_enabled(monkeypatch, tmp_path):
    import config

    db_file = tmp_path / "seed.db"
    monkeypatch.setattr(config, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{db_file}")
    monkeypatch.setattr(config, "SEED_DEMO_DATA", True)

    import app as app_module
    from models import Child

    application = app_module.create_app()
    with application.app_context():
        assert Child.query.count() == len(config.DEMO_CHILDREN)
        assert Child.query.count() > 0
        # key worker linked to a seeded Staff row
        first = Child.query.first()
        assert first.key_worker is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_incidents.py::test_demo_children_seeded_when_enabled -v`
Expected: FAIL — `AttributeError: module 'config' has no attribute 'DEMO_CHILDREN'`.

- [ ] **Step 3: Add `DEMO_CHILDREN` and enable the flag in `config.py`**

Replace the existing line `SEED_DEMO_DATA = False` with:

```python
SEED_DEMO_DATA = True

# Elevi generici de demonstrație (NU nume reale). Folosiți doar dacă
# SEED_DEMO_DATA este True. keyWorker referă un nume din STAFF.
DEMO_CHILDREN = [
    {"name": "Student A", "room": "Room 1", "age": 8, "support": "High", "keyWorker": "Staff Member 1"},
    {"name": "Student B", "room": "Room 2", "age": 9, "support": "Medium", "keyWorker": "Staff Member 2"},
    {"name": "Student C", "room": "Room 3", "age": 10, "support": "Low", "keyWorker": "Staff Member 3"},
    {"name": "Student D", "room": "Room 4", "age": 11, "support": "High", "keyWorker": "Staff Member 4"},
]
```

- [ ] **Step 4: Add the seed branch in `app.py`**

In `seed_lookups()`, after the `Staff` seeding block, add:

```python
    if config.SEED_DEMO_DATA and Child.query.count() == 0:
        staff_by_name = {s.name: s for s in Staff.query.all()}
        for d in config.DEMO_CHILDREN:
            db.session.add(
                Child(
                    name=d["name"],
                    room=d["room"],
                    age=d.get("age"),
                    support=d.get("support"),
                    key_worker=staff_by_name.get(d.get("keyWorker")),
                )
            )
        db.session.commit()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_incidents.py::test_demo_children_seeded_when_enabled -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add config.py app.py tests/test_incidents.py
git commit -m "feat: seed generic demo children when SEED_DEMO_DATA is on"
```

---

## Task 5: `POST /api/incidents` endpoint (TDD)

**Files:**
- Modify: `app.py` (import `request` and `datetime`; add route in `register_routes`; refactor `api_incidents`)
- Test: `tests/test_incidents.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_incidents.py`:

```python
def _valid_payload(child_id):
    return {
        "childId": child_id,
        "date": "2026-06-11",
        "time": "09:30",
        "type": "Crisis",
        "severity": "High",
        "trigger": "Noise",
        "description": "Test incident",
        "duration": 10,
        "outcome": "De-escalated",
        "staff": "Staff Member 1",
        "notes": "Some notes",
        "interventions": ["Calm Space", "Unknown X"],
    }


def test_post_valid_incident_persists(app, client, child_id):
    res = client.post("/api/incidents", json=_valid_payload(child_id))
    assert res.status_code == 201
    body = res.get_json()
    assert body["childId"] == child_id
    assert body["status"] == "Resolved"
    assert body["notes"] == "Some notes"
    assert "Calm Space" in body["interventions"]
    assert "Unknown X" not in body["interventions"]  # unknown ignored

    from models import Incident

    with app.app_context():
        inc = Incident.query.get(body["id"])
        assert inc is not None
        assert inc.notes == "Some notes"
        assert inc.staff.name == "Staff Member 1"
        assert inc.occurred_at.strftime("%Y-%m-%d %H:%M") == "2026-06-11 09:30"

    listed = client.get("/api/incidents").get_json()
    assert any(x["id"] == body["id"] for x in listed)


def test_post_missing_required_returns_400(client, child_id):
    res = client.post("/api/incidents", json={"childId": child_id, "date": "2026-06-11"})
    assert res.status_code == 400


def test_post_unknown_child_returns_400(client):
    payload = _valid_payload(99999)
    res = client.post("/api/incidents", json=payload)
    assert res.status_code == 400


def test_post_invalid_type_returns_400(client, child_id):
    payload = _valid_payload(child_id)
    payload["type"] = "Bogus"
    res = client.post("/api/incidents", json=payload)
    assert res.status_code == 400


def test_post_invalid_severity_returns_400(client, child_id):
    payload = _valid_payload(child_id)
    payload["severity"] = "Critical"
    res = client.post("/api/incidents", json=payload)
    assert res.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_incidents.py -k post -v`
Expected: FAIL — `405 Method Not Allowed` (route only supports GET).

- [ ] **Step 3: Update imports in `app.py`**

Change line 17 and 19:

```python
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request
```

- [ ] **Step 4: Add the POST route inside `register_routes`**

Add after the existing `api_incidents` function:

```python
    @app.route("/api/incidents", methods=["POST"])
    def create_incident():
        data = request.get_json(silent=True) or {}

        required = ["childId", "date", "time", "type", "severity", "description"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": "Missing required fields: " + ", ".join(missing)}), 400

        child = db.session.get(Child, data["childId"])
        if child is None:
            return jsonify({"error": "Unknown childId"}), 400

        if data["type"] not in config.INCIDENT_TYPES:
            return jsonify({"error": "Invalid incident type"}), 400
        if data["severity"] not in config.SEVERITY_LEVELS:
            return jsonify({"error": "Invalid severity"}), 400

        try:
            occurred_at = datetime.strptime(
                f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid date/time"}), 400

        staff = (
            Staff.query.filter_by(name=data.get("staff")).first()
            if data.get("staff")
            else None
        )
        names = data.get("interventions") or []
        interventions = (
            Intervention.query.filter(Intervention.name.in_(names)).all()
            if names
            else []
        )

        incident = Incident(
            child_id=child.id,
            staff_id=staff.id if staff else None,
            occurred_at=occurred_at,
            type=data["type"],
            severity=data["severity"],
            trigger=data.get("trigger"),
            description=data.get("description"),
            duration=data.get("duration"),
            outcome=data.get("outcome"),
            status="Resolved",
            notes=data.get("notes"),
        )
        incident.interventions = interventions
        db.session.add(incident)
        db.session.commit()
        return jsonify(_serialize_incident(incident)), 201
```

- [ ] **Step 5: Refactor `api_incidents` to reuse the serializer (DRY)**

Replace the body of `api_incidents` (lines ~126-144) with:

```python
    @app.route("/api/incidents")
    def api_incidents():
        items = Incident.query.order_by(Incident.occurred_at.desc()).all()
        return jsonify([_serialize_incident(i) for i in items])
```

- [ ] **Step 6: Run all tests to verify they pass**

Run: `pytest tests/ -v`
Expected: all PASS (smoke, notes, demo seed, 5 POST tests).

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_incidents.py
git commit -m "feat: add create-only POST /api/incidents endpoint"
```

---

## Task 6: Wire the frontend (async saveIncident)

**Files:**
- Modify: `templates/dashboard.html` (the `saveIncident()` function inside the `{% raw %}` script block)

- [ ] **Step 1: Replace `saveIncident()`**

Find the existing `function saveIncident(){ ... }` and replace it entirely with:

```javascript
async function saveIncident(){
  const childId=parseInt(document.getElementById('f-child').value);
  const date=document.getElementById('f-date').value;
  const time=document.getElementById('f-time').value;
  const type=document.getElementById('f-type').value;
  const trigger=document.getElementById('f-trigger').value;
  const desc=document.getElementById('f-desc').value.trim();
  const duration=parseInt(document.getElementById('f-duration').value)||0;
  const outcome=document.getElementById('f-outcome').value;
  const staff=document.getElementById('f-staff').value;
  const notes=document.getElementById('f-notes').value.trim();
  if(!childId){alert('Please add a child first (Settings) and select one.');return;}
  if(!desc){alert('Please enter a behaviour description.');return;}
  if(!selectedSeverity){alert('Please select a severity level.');return;}
  const payload={childId,date,time,type,severity:selectedSeverity,trigger,
    description:desc,duration,outcome,staff,notes,interventions:[...selectedInterventions]};
  try{
    const res=await fetch('/api/incidents',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!res.ok){
      const e=await res.json().catch(()=>({}));
      alert('Save failed: '+(e.error||('HTTP '+res.status)));
      return;
    }
    const saved=await res.json();
    INCIDENTS.push(saved);
    selectedInterventions=new Set();
    selectedSeverity='';
    showToast('Incident saved');
    showTab('dashboard');
  }catch(err){
    alert('Network error: '+err.message);
  }
}
```

- [ ] **Step 2: Verify the template still renders (no Jinja/JS breakage)**

Run: `pytest tests/test_incidents.py::test_dashboard_renders -v`
Expected: PASS (template compiles and renders 200).

- [ ] **Step 3: Manual end-to-end check in the browser**

Run: `python app.py` (then open http://127.0.0.1:5000/)
Do: go to **Log Incident**, pick a demo child (Student A–D), fill description, pick severity, click **Save Incident**.
Expected: green toast "Incident saved"; dashboard now shows the incident in Recent Incidents; refreshing the page keeps it (persisted in SQLite). Stop the server with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: persist incidents via async POST in saveIncident"
```

---

## Task 7: Update developer notes

**Files:**
- Modify: `DEVELOPER_NOTES.md` (the "Task-uri rămase (post-pas 5)" section)

- [ ] **Step 1: Tick the persistence item**

Change the line:

```
- Persistare formular: `POST /api/incidents` (acum `saveIncident()` salvează doar in-memory).
```

to:

```
- [x] Persistare formular: `POST /api/incidents` implementat; `saveIncident()` salvează în SQLite. Demo children seed-uite generic.
```

- [ ] **Step 2: Commit**

```bash
git add DEVELOPER_NOTES.md
git commit -m "docs: mark incident persistence done in developer notes"
```

---

## Done criteria

- `pytest tests/ -v` is green (8 tests).
- Logging an incident in the browser persists it across a page reload.
- No real school data introduced; demo children are generic.
