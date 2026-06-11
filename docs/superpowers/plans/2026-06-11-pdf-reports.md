# Real PDF Reports (Individual Child) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a real, downloadable PDF report for an individual child over a rolling time window, built from the child's actual incident data.

**Architecture:** A pure-logic module `reports.py` (period math + data aggregation + ReportLab rendering, no Flask/DB-session coupling) is driven by a thin Flask blueprint `reports_api.py` that queries incidents and streams the PDF as a download. The Reports tab's Generate button is wired to hit the endpoint for the "Individual Child" type. Data correctness is tested on the pure functions; the endpoint is tested for a valid PDF + headers.

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, SQLite, ReportLab (pure-Python PDF), pytest, vanilla JS.

---

## File Structure

- `requirements.txt` (modify) — add `reportlab`.
- `reports.py` (create) — `period_start`, `build_child_report` (pure aggregation), `render_child_report_pdf` (ReportLab).
- `reports_api.py` (create) — `GET /api/reports/child/<id>` blueprint.
- `app.py` (modify) — register `reports_bp`.
- `tests/test_reports.py` (create) — pure-function tests + endpoint tests.
- `templates/dashboard.html` (modify) — wire the Generate button (`generateReport()`), give the child `<select>` an id and option values.
- `DEVELOPER_NOTES.md` (modify) — tick the PDF reports item.

---

## Task 1: Add the ReportLab dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Confirm the suite is green before starting**

Run: `python -m pytest -q`
Expected: all PASS (34) — the baseline.

- [ ] **Step 2: Install ReportLab into the environment**

Run (PowerShell): `python -m pip install "reportlab>=4.0"`
Expected: installs reportlab and its dependency (pillow may come along). Ends with "Successfully installed reportlab-…".

- [ ] **Step 3: Verify it imports**

Run: `python -c "import reportlab; print(reportlab.Version)"`
Expected: prints a version string like `4.x`.

- [ ] **Step 4: Add it to `requirements.txt`**

The file currently is:
```
Flask>=3.0
Flask-SQLAlchemy>=3.1
```
Make it:
```
Flask>=3.0
Flask-SQLAlchemy>=3.1
reportlab>=4.0
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "build: add reportlab dependency for PDF reports"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 2: `reports.py` — period math + data aggregation (pure)

Pure functions with no Flask/DB-session use. `build_child_report` reads only attributes
off the passed objects, so tests use lightweight `SimpleNamespace` stand-ins (no DB needed).

**Files:**
- Create: `reports.py`
- Create: `tests/test_reports.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reports.py`:

```python
from datetime import date, datetime
from types import SimpleNamespace


def test_period_start_windows():
    from reports import period_start

    today = date(2026, 6, 11)
    assert period_start("week", today) == date(2026, 6, 5)    # today - 6
    assert period_start("month", today) == date(2026, 5, 13)  # today - 29
    assert period_start("term", today) == date(2026, 3, 14)   # today - 89


def test_period_start_invalid_raises():
    import pytest
    from reports import period_start

    with pytest.raises(ValueError):
        period_start("decade", date(2026, 6, 11))


def test_build_child_report_aggregates():
    from reports import build_child_report

    child = SimpleNamespace(
        name="Cian M.",
        room=SimpleNamespace(name="Room 1"),
        key_worker=SimpleNamespace(name="Staff Member 1"),
    )
    incidents = [  # already sorted desc by occurred_at
        SimpleNamespace(occurred_at=datetime(2026, 6, 10, 9, 0), type="Behavioural",
                        severity="High", trigger="Sensory", outcome="De-escalated", duration=10),
        SimpleNamespace(occurred_at=datetime(2026, 6, 9, 14, 0), type="Behavioural",
                        severity="Medium", trigger="Sensory", outcome="Resolved", duration=20),
        SimpleNamespace(occurred_at=datetime(2026, 6, 8, 9, 30), type="Crisis",
                        severity="Medium", trigger="Transition", outcome="Resolved", duration=None),
    ]
    r = build_child_report(child, incidents, "month", date(2026, 6, 11))

    assert r["child_name"] == "Cian M."
    assert r["room_name"] == "Room 1"
    assert r["key_worker"] == "Staff Member 1"
    assert r["total_incidents"] == 3
    assert r["per_week_avg"] == 0.7              # 3 / (30/7)
    assert r["top_severity"] == "Medium"         # 2x Medium vs 1x High
    assert r["avg_duration"] == "15 min"         # (10+20)/2
    assert r["top_trigger"] == "Sensory"         # 2x
    assert r["top_type"] == "Behavioural"        # 2x
    assert r["peak_time"].startswith("Morning")  # hours 9, 14, 9 -> Morning x2
    assert len(r["incident_rows"]) == 3
    assert r["incident_rows"][0]["date"] == "10 Jun 2026"


def test_build_child_report_empty():
    from reports import build_child_report

    child = SimpleNamespace(name="Empty Kid", room=None, key_worker=None)
    r = build_child_report(child, [], "week", date(2026, 6, 11))

    assert r["total_incidents"] == 0
    assert r["per_week_avg"] == 0.0
    assert r["top_severity"] == "—"
    assert r["avg_duration"] == "N/A"
    assert r["room_name"] == "—"
    assert r["key_worker"] == "—"
    assert r["pattern_text"] == "No incidents recorded in this period."
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_reports.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reports'`.

- [ ] **Step 3: Create `reports.py` with the pure functions**

```python
"""reports.py — construirea rapoartelor de comportament (date + PDF).

Agregarea (period_start, build_child_report) este pură: primește modele deja
încărcate și liste, nu atinge sesiunea DB sau Flask — ușor de testat.
Randarea PDF (render_child_report_pdf) folosește ReportLab Platypus.
"""

from collections import Counter
from datetime import timedelta
from io import BytesIO


_WINDOW_DAYS = {"week": 7, "month": 30, "term": 90}

_PERIOD_LABEL = {
    "week": "Last 7 days",
    "month": "Last 30 days",
    "term": "Last 90 days",
}

_PEAK_LABEL = {
    "Morning": "Morning (before 12:00)",
    "Afternoon": "Afternoon (12:00–17:00)",
    "Evening": "Evening (after 17:00)",
}


def period_start(period, today):
    """Data de început (inclusiv) a ferestrei rolling pentru `period`."""
    if period not in _WINDOW_DAYS:
        raise ValueError(f"Unknown period: {period!r}")
    return today - timedelta(days=_WINDOW_DAYS[period] - 1)


def _mode(values):
    """Cea mai frecventă valoare non-goală; egalități sparte de prima apariție."""
    items = [v for v in values if v]
    if not items:
        return "—"
    counts = Counter(items)
    best = max(counts.values())
    for v in items:
        if counts[v] == best:
            return v
    return "—"


def _peak_time(incidents):
    if not incidents:
        return "—"
    buckets = []
    for i in incidents:
        h = i.occurred_at.hour
        if h < 12:
            buckets.append("Morning")
        elif h < 17:
            buckets.append("Afternoon")
        else:
            buckets.append("Evening")
    counts = Counter(buckets)
    best = max(counts.values())
    for name in ("Morning", "Afternoon", "Evening"):   # tie-break order
        if counts.get(name, 0) == best:
            return _PEAK_LABEL[name]
    return "—"


def build_child_report(child, incidents, period, today):
    """View-model pur (dict) pentru raportul unui copil. `school` e completat de endpoint."""
    window_days = _WINDOW_DAYS[period]
    start = today - timedelta(days=window_days - 1)
    total = len(incidents)

    per_week_avg = round(total / (window_days / 7.0), 1)
    top_severity = _mode([i.severity for i in incidents])
    durations = [i.duration for i in incidents if i.duration is not None]
    avg_duration = f"{round(sum(durations) / len(durations))} min" if durations else "N/A"
    top_trigger = _mode([i.trigger for i in incidents])
    top_type = _mode([i.type for i in incidents])
    peak_time = _peak_time(incidents)

    rows = [
        {
            "date": i.occurred_at.strftime("%d %b %Y"),
            "type": i.type or "—",
            "severity": i.severity or "—",
            "trigger": i.trigger or "—",
            "outcome": i.outcome or "—",
        }
        for i in incidents
    ]

    if total == 0:
        pattern_text = "No incidents recorded in this period."
    else:
        parts = []
        if top_type != "—":
            parts.append(f"Most incidents were {top_type} type")
        if top_trigger != "—":
            parts.append(f"most often triggered by {top_trigger}")
        if peak_time != "—":
            parts.append(f"with a peak in the {peak_time.split(' (')[0].lower()}")
        pattern_text = (", ".join(parts) + ".") if parts else "Incidents were recorded in this period."

    return {
        "school": "",
        "child_name": child.name,
        "room_name": child.room.name if child.room else "—",
        "key_worker": child.key_worker.name if child.key_worker else "—",
        "period_label": _PERIOD_LABEL[period],
        "period_range": f"{start.strftime('%d %b %Y')} – {today.strftime('%d %b %Y')}",
        "generated_on": today.strftime("%d %b %Y"),
        "total_incidents": total,
        "per_week_avg": per_week_avg,
        "top_severity": top_severity,
        "avg_duration": avg_duration,
        "incident_rows": rows,
        "top_trigger": top_trigger,
        "top_type": top_type,
        "peak_time": peak_time,
        "pattern_text": pattern_text,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_reports.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add reports.py tests/test_reports.py
git commit -m "feat: add pure report aggregation (period math + child stats)"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 3: `reports.py` — `render_child_report_pdf` (ReportLab)

**Files:**
- Modify: `reports.py` (append the renderer)
- Modify: `tests/test_reports.py` (append the smoke test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_reports.py`:

```python
def test_render_child_report_pdf_returns_pdf_bytes():
    from reports import render_child_report_pdf

    report = {
        "school": "Test School", "child_name": "Cian M.", "room_name": "Room 1",
        "key_worker": "Staff Member 1", "period_label": "Last 30 days",
        "period_range": "13 May 2026 – 11 Jun 2026", "generated_on": "11 Jun 2026",
        "total_incidents": 1, "per_week_avg": 0.2, "top_severity": "Medium",
        "avg_duration": "10 min",
        "incident_rows": [{"date": "10 Jun 2026", "type": "Behavioural",
                           "severity": "Medium", "trigger": "Sensory", "outcome": "Resolved"}],
        "top_trigger": "Sensory", "top_type": "Behavioural",
        "peak_time": "Morning (before 12:00)",
        "pattern_text": "Most incidents were Behavioural type.",
    }
    out = render_child_report_pdf(report)
    assert isinstance(out, (bytes, bytearray))
    assert out[:4] == b"%PDF"


def test_render_child_report_pdf_empty_state():
    from reports import render_child_report_pdf

    report = {
        "school": "Test School", "child_name": "Empty Kid", "room_name": "—",
        "key_worker": "—", "period_label": "Last 7 days",
        "period_range": "05 Jun 2026 – 11 Jun 2026", "generated_on": "11 Jun 2026",
        "total_incidents": 0, "per_week_avg": 0.0, "top_severity": "—",
        "avg_duration": "N/A", "incident_rows": [], "top_trigger": "—",
        "top_type": "—", "peak_time": "—",
        "pattern_text": "No incidents recorded in this period.",
    }
    out = render_child_report_pdf(report)
    assert out[:4] == b"%PDF"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_reports.py -k pdf -v`
Expected: FAIL — `AttributeError`/`ImportError` (no `render_child_report_pdf`).

- [ ] **Step 3: Append the renderer to `reports.py`**

```python
def render_child_report_pdf(report):
    """Construiește PDF-ul raportului în memorie și întoarce bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="EDI AI Behaviour Report",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("rh1", parent=styles["Title"], fontSize=18, spaceAfter=2)
    sub = ParagraphStyle("rsub", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    h2 = ParagraphStyle("rh2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
    body = styles["Normal"]

    story = []
    story.append(Paragraph("EDI AI Behaviour Report", h1))
    story.append(Paragraph(
        f"Generated by EDI AI · {report['school']} · {report['generated_on']}", sub))
    story.append(Spacer(1, 8))

    meta = [
        ["Child:", report["child_name"], "Class:", report["room_name"]],
        ["Period:", f"{report['period_label']} ({report['period_range']})",
         "Key Worker:", report["key_worker"]],
    ]
    meta_tbl = Table(meta, colWidths=[22 * mm, 60 * mm, 24 * mm, 48 * mm])
    meta_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 8))

    stats = [
        [str(report["total_incidents"]), str(report["per_week_avg"]),
         report["top_severity"], report["avg_duration"]],
        ["Total Incidents", "Per Week Avg", "Top Severity", "Avg Duration"],
    ]
    stats_tbl = Table(stats, colWidths=[44 * mm] * 4)
    stats_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, 0), 15),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 8),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.grey),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stats_tbl)

    story.append(Paragraph("Incident Summary", h2))
    if report["incident_rows"]:
        data = [["Date", "Type", "Severity", "Trigger", "Outcome"]]
        for row in report["incident_rows"]:
            data.append([row["date"], row["type"], row["severity"], row["trigger"], row["outcome"]])
        tbl = Table(data, colWidths=[26 * mm, 34 * mm, 24 * mm, 34 * mm, 36 * mm], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No incidents recorded in this period.", body))

    story.append(Paragraph("Pattern Analysis", h2))
    story.append(Paragraph(report["pattern_text"], body))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"Generated by EDI AI · {report['school']}  |  CONFIDENTIAL", sub))

    doc.build(story)
    return buffer.getvalue()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_reports.py -k pdf -v`
Expected: both PDF tests PASS.

- [ ] **Step 5: Commit**

```bash
git add reports.py tests/test_reports.py
git commit -m "feat: render child behaviour report to PDF with ReportLab"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 4: `reports_api.py` blueprint + registration

**Files:**
- Create: `reports_api.py`
- Modify: `app.py` (register the blueprint in `create_app`)
- Modify: `tests/test_reports.py` (endpoint tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_reports.py`:

```python
def test_child_report_pdf_download(client, child_id):
    res = client.get(f"/api/reports/child/{child_id}?period=month")
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert res.data[:4] == b"%PDF"
    cd = res.headers["Content-Disposition"]
    assert "Test_Child" in cd and ".pdf" in cd


def test_child_report_default_period(client, child_id):
    res = client.get(f"/api/reports/child/{child_id}")
    assert res.status_code == 200
    assert res.data[:4] == b"%PDF"


def test_child_report_unknown_child_returns_404(client):
    res = client.get("/api/reports/child/99999")
    assert res.status_code == 404


def test_child_report_invalid_period_returns_400(client, child_id):
    res = client.get(f"/api/reports/child/{child_id}?period=decade")
    assert res.status_code == 400


def test_child_report_with_incident_still_pdf(app, client, child_id):
    from datetime import datetime
    from models import db, Incident

    with app.app_context():
        db.session.add(Incident(
            child_id=child_id, occurred_at=datetime(2026, 6, 11, 9, 30),
            type="Crisis", severity="High", trigger="Sensory",
            outcome="De-escalated", duration=12,
        ))
        db.session.commit()

    res = client.get(f"/api/reports/child/{child_id}?period=term")
    assert res.status_code == 200
    assert res.data[:4] == b"%PDF"
```

Note: the `child_id` fixture (in `tests/conftest.py`) creates a child named "Test Child" with no incidents, so the default-period download exercises the empty-state path.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_reports.py -k report -v`
Expected: the endpoint tests FAIL with `404 Not Found` (no `/api/reports/...` route yet).

- [ ] **Step 3: Create `reports_api.py`**

```python
"""reports_api.py — endpoint-uri de generare rapoarte (PDF).

Înregistrat sub /api de app.create_app(). v1: raport pentru un copil individual,
generat la cerere și trimis ca download (fără stocare pe disc).
"""

import re
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, jsonify, request

from models import db, Child, Incident, SystemConfig
from serializers import serialize_system_config
from reports import period_start, build_child_report, render_child_report_pdf

reports_bp = Blueprint("reports", __name__, url_prefix="/api")


@reports_bp.route("/reports/child/<int:child_id>", methods=["GET"])
def child_report(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404

    period = request.args.get("period", "month")
    today = date.today()
    try:
        start = period_start(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())
    incidents = (
        Incident.query
        .filter(Incident.child_id == child_id,
                Incident.occurred_at >= start_dt,
                Incident.occurred_at < end_dt)
        .order_by(Incident.occurred_at.desc())
        .all()
    )

    report = build_child_report(child, incidents, period, today)
    report["school"] = serialize_system_config(SystemConfig.query.first())["name"]
    pdf = render_child_report_pdf(report)

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", child.name).strip("_") or "child"
    filename = f"EDI_AI_Report_{safe_name}_{period}_{today:%Y%m%d}.pdf"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 4: Register the blueprint in `app.py`**

In `create_app()` there is already a block registering the settings blueprint:
```python
    from settings_api import settings_bp
    app.register_blueprint(settings_bp)
```
Immediately after it (and before `return app`), add:
```python
    from reports_api import reports_bp
    app.register_blueprint(reports_bp)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_reports.py -v`
Expected: all report tests PASS. Then run the full suite `python -m pytest -q` — expected all green.

- [ ] **Step 6: Commit**

```bash
git add reports_api.py app.py tests/test_reports.py
git commit -m "feat: add GET /api/reports/child/<id> PDF download endpoint"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 5: Frontend — wire the Generate button

This task is verified by template-render (the existing dashboard render test) plus a manual
browser pass; the JS is not unit-tested.

**Files:**
- Modify: `templates/dashboard.html` (`renderReports()` + a new `generateReport()`)

- [ ] **Step 1: Give the child select an id and option values**

In `renderReports()`, find:
```javascript
  const childOpts=CHILDREN.map(c=>`<option>${c.name}</option>`).join('')||'<option value="">No children added yet</option>';
```
Replace with:
```javascript
  const childOpts=CHILDREN.map(c=>`<option value="${c.id}">${c.name}</option>`).join('')||'<option value="">No children added yet</option>';
```

Then find:
```javascript
      <div class="form-group" id="r-child-wrap">
        <label>Child</label>
        <select>${childOpts}</select>
      </div>
```
Replace with:
```javascript
      <div class="form-group" id="r-child-wrap">
        <label>Child</label>
        <select id="r-child">${childOpts}</select>
      </div>
```

- [ ] **Step 2: Wire the Generate button to `generateReport()`**

Find:
```javascript
        <button class="btn-accent" style="width:100%;padding:11px" onclick="showToast('Report generation not yet implemented')">&#128196; Generate Report</button>
```
Replace with:
```javascript
        <button class="btn-accent" style="width:100%;padding:11px" onclick="generateReport()">&#128196; Generate Report</button>
```

- [ ] **Step 3: Add the `generateReport()` function**

Immediately after the `toggleReportChild()` function, add:
```javascript
function generateReport(){
  const type=document.getElementById('r-type').value;
  if(type!=='Individual Child'){showToast('Report generation not yet implemented');return;}
  const id=document.getElementById('r-child').value;
  if(!id){alert('Please select a child.');return;}
  const periodMap={'This Week':'week','This Month':'month','This Term':'term'};
  const period=periodMap[document.getElementById('r-period').value]||'month';
  window.location='/api/reports/child/'+id+'?period='+period;
}
```

- [ ] **Step 4: Verify the template still renders**

Run: `python -m pytest tests/test_settings.py::test_dashboard_reflects_system_config -v`
Expected: PASS (the dashboard template compiles and renders).

- [ ] **Step 5: Manual browser check**

Run: `python app.py` (open http://127.0.0.1:5000/). First go to **Settings** (or **Log Incident**)
and make sure at least one child exists and has a logged incident or two. Then go to **Reports**:
1. Report Type **Individual Child**, pick the child, Time Period **This Month**, click **Generate Report** → the browser downloads `EDI_AI_Report_<Name>_month_<date>.pdf`. Open it: header shows the school name, meta shows child/class/period/key worker, stats and the Incident Summary table reflect that child's incidents.
2. Pick a child with no incidents in the window (or period **This Week** with none) → the PDF still downloads and shows "No incidents recorded in this period."
3. Switch Report Type to **Class Summary** → Generate shows the "not yet implemented" toast.
4. Stop the server with Ctrl+C.

Expected: a real PDF downloads for Individual Child; empty windows still produce a valid PDF; the other report types still show the toast.

- [ ] **Step 6: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: wire Reports Generate button to PDF download for Individual Child"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 6: Update developer notes

**Files:**
- Modify: `DEVELOPER_NOTES.md`

- [ ] **Step 1: Replace the PDF reports line**

Find:
```
- Generare reală rapoarte PDF.
```
Replace with:
```
- [x] Generare reală rapoarte PDF: raport Individual Child (ReportLab, pure-Python), `GET /api/reports/child/<id>?period=week|month|term`, download on-the-fly din datele reale de incidente. Class Summary / Whole School rămân fast-follow.
```

- [ ] **Step 2: Commit**

```bash
git add DEVELOPER_NOTES.md
git commit -m "docs: mark real PDF reports (Individual Child) done"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Done criteria

- `python -m pytest -q` is green (existing 34 + the new report tests).
- From Reports → Individual Child, selecting a child + period and clicking Generate downloads
  a real `.pdf` whose stats/table reflect that child's incidents in the rolling window.
- A child with no incidents in the window still produces a valid PDF (empty-state text).
- Class Summary / Whole School keep the existing "not yet implemented" toast.
- `reportlab>=4.0` is in `requirements.txt`.
