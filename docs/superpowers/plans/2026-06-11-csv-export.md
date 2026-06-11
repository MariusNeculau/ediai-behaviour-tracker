# CSV Export of Incidents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-click "Export All Incidents (CSV)" action in the Reports tab that downloads every incident as an Excel-friendly UTF-8 CSV.

**Architecture:** A pure `exports.py` builds the CSV string from incident model instances; a `GET /api/export/incidents.csv` endpoint queries all incidents, prepends a UTF-8 BOM, and streams the file; the Reports tab gets a button wired to the endpoint.

**Tech Stack:** Python (stdlib `csv`), Flask, pytest, vanilla JS.

---

## File Structure

- `exports.py` (create) — `incidents_to_csv(incidents) -> str` + `CSV_HEADER`.
- `reports_api.py` (modify) — `GET /api/export/incidents.csv`.
- `templates/dashboard.html` (modify) — Export button in `renderReports()` + `exportIncidentsCsv()`.
- `tests/test_exports.py` (create) — pure + endpoint tests.
- `DEVELOPER_NOTES.md` (modify) — note the CSV export.

---

## Task 1: Confirm baseline

- [ ] **Step 1: Run the suite**

Run: `python -m pytest -q`
Expected: all PASS (61). No schema change.

---

## Task 2: `exports.py` — pure CSV builder

**Files:** Create `exports.py`, `tests/test_exports.py`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_exports.py`:

```python
from datetime import datetime
from types import SimpleNamespace


def _inc(**kw):
    base = dict(
        occurred_at=datetime(2026, 6, 10, 9, 30),
        child=SimpleNamespace(name="Alice", room=SimpleNamespace(name="Room 1")),
        type="Behavioural", severity="High", trigger="Sensory",
        duration=10, outcome="De-escalated",
        interventions=[SimpleNamespace(name="Calm Space"), SimpleNamespace(name="Sensory Tool")],
        staff=SimpleNamespace(name="Staff Member 1"), status="Resolved",
        description="hit out", notes="follow up",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_incidents_to_csv_header_and_row():
    from exports import incidents_to_csv, CSV_HEADER

    out = incidents_to_csv([_inc()])
    lines = out.strip().split("\n")
    assert lines[0] == ",".join(CSV_HEADER)
    row = lines[1]
    assert "Alice" in row
    assert "Room 1" in row
    assert "Calm Space; Sensory Tool" in row
    assert "Staff Member 1" in row
    assert "2026-06-10" in row and "09:30" in row


def test_incidents_to_csv_empty():
    from exports import incidents_to_csv

    out = incidents_to_csv([])
    assert out.strip().count("\n") == 0   # only the header line
    assert out.startswith("Date,Time,Child")


def test_incidents_to_csv_handles_missing():
    from exports import incidents_to_csv

    inc = _inc(child=None, staff=None, duration=None, interventions=[],
               notes=None, description=None)
    out = incidents_to_csv([inc])
    lines = out.strip().split("\n")
    assert lines[1].count(",") == 13   # 14 columns -> 13 separators, no embedded commas
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_exports.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'exports'`.

- [ ] **Step 3: Create `exports.py`**

```python
"""exports.py — export tabular (CSV) al datelor.

Pur: primește instanțe de model deja încărcate, nu atinge Flask/sesiunea DB.
"""

import csv
import io

CSV_HEADER = [
    "Date", "Time", "Child", "Class", "Type", "Severity", "Trigger",
    "Duration (min)", "Interventions", "Outcome", "Key Worker", "Status",
    "Description", "Notes",
]


def incidents_to_csv(incidents):
    """Întoarce un string CSV (antet + un rând per incident)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for i in incidents:
        dt = i.occurred_at
        writer.writerow([
            dt.strftime("%Y-%m-%d") if dt else "",
            dt.strftime("%H:%M") if dt else "",
            i.child.name if i.child else "",
            i.child.room.name if (i.child and i.child.room) else "",
            i.type or "",
            i.severity or "",
            i.trigger or "",
            i.duration if i.duration is not None else "",
            "; ".join(iv.name for iv in i.interventions),
            i.outcome or "",
            i.staff.name if i.staff else "",
            i.status or "",
            i.description or "",
            i.notes or "",
        ])
    return buf.getvalue()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_exports.py -v`
Expected: all three PASS. Then `python -m pytest -q` → all green.

- [ ] **Step 5: Commit**

```bash
git add exports.py tests/test_exports.py
git commit -m "feat: add pure incidents_to_csv CSV builder"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 3: `reports_api.py` — CSV export endpoint

**Files:** Modify `reports_api.py`, `tests/test_exports.py`.

- [ ] **Step 1: Write the failing endpoint tests**

Append to `tests/test_exports.py`:

```python
def test_export_incidents_csv_download(client):
    res = client.get("/api/export/incidents.csv")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    assert ".csv" in res.headers["Content-Disposition"]
    text = res.get_data(as_text=True)
    assert text[0] == "﻿"               # UTF-8 BOM for Excel
    assert "Date,Time,Child" in text


def test_export_incidents_csv_includes_row(app, client, child_id):
    from datetime import datetime
    from models import db, Incident

    with app.app_context():
        db.session.add(Incident(
            child_id=child_id, occurred_at=datetime(2026, 6, 10, 9, 30),
            type="Crisis", severity="High",
        ))
        db.session.commit()

    text = client.get("/api/export/incidents.csv").get_data(as_text=True)
    assert "2026-06-10" in text
    assert "Crisis" in text
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_exports.py -k export -v`
Expected: FAIL — `404 Not Found` (no `/api/export/...` route yet).

- [ ] **Step 3: Add the import to `reports_api.py`**

After the existing `from reports import (...)` import block, add:
```python
from exports import incidents_to_csv
```
(`date` and `Incident` and `Response` are already imported in `reports_api.py`.)

- [ ] **Step 4: Append the endpoint to `reports_api.py`**

Add at the end of the file:
```python
@reports_bp.route("/export/incidents.csv", methods=["GET"])
def export_incidents_csv():
    incidents = Incident.query.order_by(Incident.occurred_at.desc()).all()
    body = "﻿" + incidents_to_csv(incidents)   # BOM so Excel detects UTF-8
    today = date.today()
    filename = f"EDI_AI_Incidents_{today:%Y%m%d}.csv"
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_exports.py -v`
Expected: all PASS. Then `python -m pytest -q` → all green.

- [ ] **Step 6: Commit**

```bash
git add reports_api.py tests/test_exports.py
git commit -m "feat: add GET /api/export/incidents.csv endpoint"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 4: Frontend button + developer notes

This task is verified by template-render (existing dashboard render test) plus a manual click; the JS is not unit-tested.

**Files:** Modify `templates/dashboard.html`, `DEVELOPER_NOTES.md`.

- [ ] **Step 1: Add the Export button in `renderReports()`**

In `renderReports()`, find:
```javascript
  <div class="recent-reports">
    <div class="card-header" style="padding:14px 18px"><div class="card-title">Recent Reports</div></div>
```
Replace with:
```javascript
  <div style="margin:0 0 22px">
    <button class="btn-outline" onclick="exportIncidentsCsv()">&#11015; Export All Incidents (CSV)</button>
  </div>

  <div class="recent-reports">
    <div class="card-header" style="padding:14px 18px"><div class="card-title">Recent Reports</div></div>
```

- [ ] **Step 2: Add the `exportIncidentsCsv()` handler**

Find the end of `generateReport()`:
```javascript
  }else{
    window.location='/api/reports/school?period='+period;
  }
}
```
Replace with:
```javascript
  }else{
    window.location='/api/reports/school?period='+period;
  }
}
function exportIncidentsCsv(){
  window.location='/api/export/incidents.csv';
}
```

- [ ] **Step 3: Verify the template still renders**

Run: `python -m pytest tests/test_settings.py::test_dashboard_reflects_system_config -v`
Expected: PASS.

- [ ] **Step 4: Manual browser check**

Run: `python app.py` (open http://127.0.0.1:5000/). Go to **Reports**, click **Export All Incidents (CSV)**.
Expected: a file `EDI_AI_Incidents_<date>.csv` downloads; opening it shows the header row and one row
per logged incident (Date, Time, Child, Class, … Notes), with accented characters intact in Excel.
Stop the server with Ctrl+C.

- [ ] **Step 5: Update `DEVELOPER_NOTES.md`**

Find the line ending the PDF reports bullet:
```
Include și Class Summary (`/api/reports/class/<room_id>`, breakdown per-elev) și Whole School (`/api/reports/school`, breakdown per-clasă), prin `render_report_pdf` generalizat.
```
Add a new bullet directly after it (same indentation as that bullet):
```
- [x] Export CSV al incidentelor: `GET /api/export/incidents.csv` (modul pur `exports.py`), buton în Reports, BOM UTF-8 pentru Excel. Dump complet, toate incidentele.
```

- [ ] **Step 6: Commit**

```bash
git add templates/dashboard.html DEVELOPER_NOTES.md
git commit -m "feat: Export All Incidents (CSV) button in Reports"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Done criteria

- `python -m pytest -q` is green (existing suite + the new export tests).
- The Reports tab has an "Export All Incidents (CSV)" button that downloads
  `EDI_AI_Incidents_<date>.csv` with every incident, openable in Excel with correct accents.
- An empty database exports a valid header-only CSV.
