# System Settings (DB-backed) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move school identity (name + roll number) from `config.py` into a single-row DB table and let a non-technical user edit it from a new System section in Settings.

**Architecture:** A new single-row `SystemConfig` model is the runtime source of truth, seeded once from `config.SCHOOL`. A `serialize_system_config()` helper produces the same `{name, roll_number}` shape the template already consumes. A `GET`/`PUT /api/system` pair on the existing settings blueprint reads/updates the row. The dashboard route serves the DB value; the Settings page replaces the read-only school info box with an editable form.

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, SQLite, pytest, vanilla JS (fetch).

---

## File Structure

- `models.py` (modify) — add a `SystemConfig` single-row model.
- `serializers.py` (modify) — add `serialize_system_config`.
- `app.py` (modify) — import `SystemConfig` + serializer; seed the row in `seed_lookups()`; serve it from the dashboard route.
- `settings_api.py` (modify) — add `GET`/`PUT /api/system`.
- `tests/test_settings.py` (modify) — model/seed + endpoint + dashboard-render tests.
- `templates/dashboard.html` (modify) — replace the read-only school info box with an editable System section + `saveSystem()`.

---

## Task 1: Remove the stale dev database (schema change)

**Files:**
- (none — local DB cleanup only)

- [ ] **Step 1: Remove any stale DB (a new table is added in Task 2)**

Run (PowerShell): `if (Test-Path instance/behaviour.db) { Remove-Item instance/behaviour.db -Force }`
Expected: no error. Blank slate; `instance/` is gitignored, no real data to lose.

- [ ] **Step 2: Confirm the suite is green before starting**

Run: `python -m pytest -q`
Expected: all existing tests PASS (27) — the baseline before changes.

---

## Task 2: SystemConfig model + serializer + seed + dashboard wiring

Add the single-row model, route its JSON through the shared serializer, seed it from
`config.SCHOOL`, and serve it from the dashboard — all in one task so the suite stays green.

**Files:**
- Modify: `models.py` (add `SystemConfig`)
- Modify: `serializers.py` (add `serialize_system_config`)
- Modify: `app.py` (imports; `seed_lookups`; dashboard route)
- Modify: `tests/test_settings.py` (model/seed test)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_settings.py`:

```python
def test_system_config_seeded_from_config(app):
    import config
    from serializers import serialize_system_config
    from models import SystemConfig

    with app.app_context():
        sc = SystemConfig.query.first()
        assert sc is not None
        assert SystemConfig.query.count() == 1
        out = serialize_system_config(sc)
        assert out["name"] == config.SCHOOL["name"]
        assert out["roll_number"] == config.SCHOOL["roll_number"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_settings.py::test_system_config_seeded_from_config -v`
Expected: FAIL — `ImportError`/`AttributeError` (no `SystemConfig`, no `serialize_system_config`).

- [ ] **Step 3: Add the `SystemConfig` model to `models.py`**

Add this class (place it above `Room`, near the top of the model definitions):

```python
class SystemConfig(db.Model):
    """Identitatea școlii (nume + roll number). Un singur rând.

    Sursa de adevăr la runtime — seed-uită o singură dată din config.SCHOOL.
    """

    __tablename__ = "system_config"

    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(120), nullable=False)
    roll_number = db.Column(db.String(40), nullable=False)

    def __repr__(self):
        return f"<SystemConfig {self.school_name!r} ({self.roll_number})>"
```

- [ ] **Step 4: Add the serializer to `serializers.py`**

Append:

```python
def serialize_system_config(sc):
    return {"name": sc.school_name, "roll_number": sc.roll_number}
```

- [ ] **Step 5: Update `app.py` imports**

Change:

```python
from models import db, Child, Staff, Room, Incident, Intervention
from serializers import serialize_child, serialize_staff, serialize_room
```

to:

```python
from models import db, Child, Staff, Room, Incident, Intervention, SystemConfig
from serializers import serialize_child, serialize_staff, serialize_room, serialize_system_config
```

- [ ] **Step 6: Seed the row in `seed_lookups()`**

At the start of `seed_lookups()` (before the `Room` seeding block), add:

```python
    if SystemConfig.query.first() is None:
        db.session.add(
            SystemConfig(
                school_name=config.SCHOOL["name"],
                roll_number=config.SCHOOL["roll_number"],
            )
        )
        db.session.commit()
```

- [ ] **Step 7: Serve the DB value from the dashboard route**

In the `dashboard()` route's `render_template(...)` call, replace:

```python
            school=config.SCHOOL,
```

with:

```python
            school=serialize_system_config(SystemConfig.query.first()),
```

- [ ] **Step 8: Run the full suite**

Run: `python -m pytest -q`
Expected: all PASS (27 existing + the new seed test). The dashboard still renders because
the served shape (`{name, roll_number}`) is unchanged.

- [ ] **Step 9: Commit**

```bash
git add models.py serializers.py app.py tests/test_settings.py
git commit -m "feat: add SystemConfig table seeded from config; serve school from DB"
```

---

## Task 3: System Settings API (GET + PUT)

**Files:**
- Modify: `settings_api.py` (append the System endpoints + import)
- Modify: `tests/test_settings.py` (endpoint tests)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_settings.py`:

```python
def test_get_system_config_defaults(client):
    import config

    body = client.get("/api/system").get_json()
    assert body["name"] == config.SCHOOL["name"]
    assert body["roll_number"] == config.SCHOOL["roll_number"]


def test_update_system_config(client):
    res = client.put("/api/system", json={"name": "Oak Primary", "roll_number": "12345B"})
    assert res.status_code == 200
    assert res.get_json() == {"name": "Oak Primary", "roll_number": "12345B"}

    body = client.get("/api/system").get_json()
    assert body["name"] == "Oak Primary"
    assert body["roll_number"] == "12345B"


def test_update_system_blank_name_returns_400(client):
    res = client.put("/api/system", json={"name": "   ", "roll_number": "12345B"})
    assert res.status_code == 400


def test_update_system_blank_roll_returns_400(client):
    res = client.put("/api/system", json={"name": "Oak Primary", "roll_number": ""})
    assert res.status_code == 400
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_settings.py -k system -v`
Expected: FAIL — `404 Not Found` (no `/api/system` route yet) for the GET/PUT tests.

- [ ] **Step 3: Add the System endpoints to `settings_api.py`**

Update the models import at the top of `settings_api.py`:

```python
from models import db, Child, Staff, Room
```

to:

```python
from models import db, Child, Staff, Room, SystemConfig
```

and the serializers import:

```python
from serializers import serialize_room, serialize_staff, serialize_child
```

to:

```python
from serializers import serialize_room, serialize_staff, serialize_child, serialize_system_config
```

Then append at the end of the file (after the Children section):

```python
# ─── System ─────────────────────────────────────────────────────────────────

@settings_bp.route("/system", methods=["GET"])
def get_system():
    return jsonify(serialize_system_config(SystemConfig.query.first()))


@settings_bp.route("/system", methods=["PUT"])
def update_system():
    sc = SystemConfig.query.first()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    roll_number = (data.get("roll_number") or "").strip()
    if not roll_number:
        return jsonify({"error": "Roll number is required"}), 400
    sc.school_name = name
    sc.roll_number = roll_number
    db.session.commit()
    return jsonify(serialize_system_config(sc))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_settings.py -k system -v`
Expected: all system tests PASS.

- [ ] **Step 5: Commit**

```bash
git add settings_api.py tests/test_settings.py
git commit -m "feat: add GET/PUT /api/system for editable school identity"
```

---

## Task 4: Dashboard reflects edited school name (render test)

**Files:**
- Modify: `tests/test_settings.py` (render test)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_settings.py`:

```python
def test_dashboard_reflects_system_config(client):
    client.put("/api/system", json={"name": "Maple Special School", "roll_number": "99999Z"})
    html = client.get("/").get_data(as_text=True)
    assert "Maple Special School" in html
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `python -m pytest tests/test_settings.py::test_dashboard_reflects_system_config -v`
Expected: PASS — the dashboard route serves the DB value, so the edited name appears in
the rendered `{{ school | tojson }}`. (This test passes immediately because Task 2 already
wired the route to the DB; it locks in the "reflected in the UI" requirement.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_settings.py
git commit -m "test: assert dashboard render reflects edited school name"
```

---

## Task 5: Frontend — editable System section in Settings

This task is verified by template-render (pytest, already covered) plus a manual browser pass; the JS is not unit-tested.

**Files:**
- Modify: `templates/dashboard.html` (replace the read-only info box in `renderSettings()`; add `saveSystem()`)

- [ ] **Step 1: Replace the read-only school info box with an editable System section**

In `renderSettings()`, find the read-only info box block:

```javascript
    <div class="settings-section" style="background:var(--gray-50);border-left:3px solid var(--primary,#2563eb)">
      <div style="display:flex;align-items:center;gap:12px">
        <div style="font-size:24px">&#127979;</div>
        <div>
          <div class="set-name" style="font-size:16px">${SCHOOL.name}</div>
          <div class="set-role">Roll Number: ${SCHOOL.roll_number||'&mdash;'} &middot; configured in config.py</div>
        </div>
      </div>
    </div>
```

Replace it with:

```javascript
    <div class="settings-section">
      <h3>&#9881; System</h3>
      <div class="form-group" style="margin-bottom:14px">
        <label>School Name</label>
        <input type="text" id="m-sys-name" value="${SCHOOL.name}">
      </div>
      <div class="form-group">
        <label>Roll Number</label>
        <input type="text" id="m-sys-roll" value="${SCHOOL.roll_number}">
      </div>
      <div style="margin-top:14px"><button class="btn-primary" style="width:auto;padding:10px 24px" onclick="saveSystem()">&#10003; Save</button></div>
    </div>
```

- [ ] **Step 2: Add the `saveSystem()` handler**

In the `// ─── SETTINGS CRUD ───` block (e.g. immediately before `function openRoomModal(id){`),
add:

```javascript
async function saveSystem(){
  const name=document.getElementById('m-sys-name').value.trim();
  const roll=document.getElementById('m-sys-roll').value.trim();
  if(!name){alert('Please enter a school name.');return;}
  if(!roll){alert('Please enter a roll number.');return;}
  try{
    const res=await fetch('/api/system',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,roll_number:roll})});
    if(!res.ok){const e=await res.json().catch(()=>({}));alert(e.error||('HTTP '+res.status));return;}
    const saved=await res.json();
    SCHOOL.name=saved.name;SCHOOL.roll_number=saved.roll_number;
    showToast('System settings saved');showTab('settings');
  }catch(err){alert('Network error: '+err.message);}
}
```

- [ ] **Step 3: Verify the template still renders**

Run: `python -m pytest tests/test_settings.py::test_dashboard_reflects_system_config -v`
Expected: PASS (the dashboard template compiles and renders with the new section).

- [ ] **Step 4: Manual browser check**

Run: `python app.py` (open http://127.0.0.1:5000/), go to **Settings → System**.
Do, in order:
1. Change **School Name** to a new value and **Roll Number** to a new value → click **Save** → green toast, fields keep the new values.
2. Go to **Reports** → the report header shows the new school name (no full reload).
3. Try saving with a blank School Name → red `alert` "Please enter a school name."; blank Roll Number → "Please enter a roll number."
4. Stop the server (Ctrl+C), restart `python app.py`, reopen Settings → the edited values persisted (loaded from DB).

Expected: edits persist across restart; Reports reflect the new name; blank fields are rejected.

- [ ] **Step 5: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: editable System section (school name + roll number) in Settings"
```

---

## Task 6: Update developer notes

**Files:**
- Modify: `DEVELOPER_NOTES.md`

- [ ] **Step 1: Add a System Settings line under the Settings CRUD entry**

After the `- [x] Settings CRUD ...` block, add:

```
- [x] System Settings: identitatea școlii (nume + roll number) mutată din `config.py` în tabelul `system_config` (single-row), editabilă din Settings → System (`GET`/`PUT /api/system`). `config.py` rămâne doar default-ul de seed.
```

- [ ] **Step 2: Commit**

```bash
git add DEVELOPER_NOTES.md
git commit -m "docs: mark System Settings done in developer notes"
```

---

## Done criteria

- `python -m pytest -q` is green (27 existing + 6 new system tests).
- School Name and Roll Number are editable from Settings → System and persist in the DB
  across a server restart.
- Both fields are required; blank input is rejected with a clear message (client and server).
- Reports headers reflect the edited school name without a code change.
- `config.py` `SCHOOL` is used only as the initial seed default.
