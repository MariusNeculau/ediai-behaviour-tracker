# PDF Management Report (Individual Child v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the individual-child PDF to a "management report": bordered Student Details, a 3-column aggregated Pattern Analysis (real counts), dynamic School Name + Roll Number from the DB, and a "Page X of Y" footer on every page.

**Architecture:** Extend the pure `build_child_report` with three count distributions plus `age`/`school_roll`, then rewrite `render_child_report_pdf` (ReportLab, lazy-imported) to lay out the new sections and a `NumberedCanvas` footer. The endpoint fills both school name and roll number. No new files; the v1 endpoint, periods, and filename are unchanged.

**Tech Stack:** Python, ReportLab (Platypus + canvas subclass), Flask, pytest.

---

## File Structure

- `reports.py` (modify) — add `_count_dist`; extend `build_child_report`; rewrite `render_child_report_pdf`.
- `reports_api.py` (modify) — fill `school` + `school_roll` from `SystemConfig`.
- `tests/test_reports.py` (modify) — new `_count_dist` test; update aggregate/empty/render tests.
- `DEVELOPER_NOTES.md` (modify) — note the management-report upgrade.

---

## Task 1: Confirm baseline

**Files:** (none)

- [ ] **Step 1: Confirm the suite is green before starting**

Run: `python -m pytest -q`
Expected: all PASS (45). No schema change in this feature, so no DB reset is needed.

---

## Task 2: `reports.py` — count distributions + new report keys

**Files:**
- Modify: `reports.py` (add `_count_dist`; extend `build_child_report`)
- Modify: `tests/test_reports.py`

- [ ] **Step 1: Update/add the failing tests**

In `tests/test_reports.py`, REPLACE the existing `test_build_child_report_aggregates` and
`test_build_child_report_empty` with the versions below, and ADD `test_count_dist_orders_by_count_then_label`:

```python
def test_count_dist_orders_by_count_then_label():
    from reports import _count_dist

    assert _count_dist(["B", "A", "A", "B", "C", "B"]) == [("B", 3), ("A", 2), ("C", 1)]
    assert _count_dist([]) == []
    assert _count_dist([None, "", "X"]) == [("X", 1)]


def test_build_child_report_aggregates():
    from reports import build_child_report

    child = SimpleNamespace(
        name="Cian M.", age=8,
        room=SimpleNamespace(name="Room 1"),
        key_worker=SimpleNamespace(name="Staff Member 1"),
    )
    incidents = [  # already sorted desc by occurred_at
        SimpleNamespace(occurred_at=datetime(2026, 6, 10, 9, 0), type="Behavioural",
                        severity="High", trigger="Sensory", outcome="De-escalated", duration=10,
                        interventions=[SimpleNamespace(name="Calm Space"), SimpleNamespace(name="Sensory Tool")]),
        SimpleNamespace(occurred_at=datetime(2026, 6, 9, 14, 0), type="Behavioural",
                        severity="Medium", trigger="Sensory", outcome="Resolved", duration=20,
                        interventions=[SimpleNamespace(name="Calm Space")]),
        SimpleNamespace(occurred_at=datetime(2026, 6, 8, 9, 30), type="Crisis",
                        severity="Medium", trigger="Transition", outcome="Resolved", duration=None,
                        interventions=[]),
    ]
    r = build_child_report(child, incidents, "month", date(2026, 6, 11))

    assert r["child_name"] == "Cian M."
    assert r["age"] == 8
    assert r["room_name"] == "Room 1"
    assert r["key_worker"] == "Staff Member 1"
    assert r["total_incidents"] == 3
    assert r["per_week_avg"] == 0.7
    assert r["top_severity"] == "Medium"
    assert r["avg_duration"] == "15 min"
    assert r["top_trigger"] == "Sensory"
    assert r["top_type"] == "Behavioural"
    assert r["peak_time"].startswith("Morning")
    assert len(r["incident_rows"]) == 3
    assert r["incident_rows"][0]["date"] == "10 Jun 2026"
    assert r["trigger_counts"] == [("Sensory", 2), ("Transition", 1)]
    assert r["behavior_counts"] == [("Behavioural", 2), ("Crisis", 1)]
    assert r["action_counts"] == [("Calm Space", 2), ("Sensory Tool", 1)]


def test_build_child_report_empty():
    from reports import build_child_report

    child = SimpleNamespace(name="Empty Kid", age=None, room=None, key_worker=None)
    r = build_child_report(child, [], "week", date(2026, 6, 11))

    assert r["total_incidents"] == 0
    assert r["per_week_avg"] == 0.0
    assert r["top_severity"] == "—"
    assert r["avg_duration"] == "N/A"
    assert r["room_name"] == "—"
    assert r["key_worker"] == "—"
    assert r["age"] == "—"
    assert r["trigger_counts"] == []
    assert r["behavior_counts"] == []
    assert r["action_counts"] == []
    assert r["pattern_text"] == "No incidents recorded in this period."
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_reports.py -k "count_dist or aggregates or empty" -v`
Expected: FAIL — `_count_dist` missing / `KeyError` on the new dict keys.

- [ ] **Step 3: Add `_count_dist` to `reports.py`**

Add this function (next to `_mode`, above `build_child_report`):

```python
def _count_dist(values):
    """[(label, count)] sortat după count desc apoi label asc; ignoră valorile goale."""
    items = [v for v in values if v]
    if not items:
        return []
    counts = Counter(items)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
```

- [ ] **Step 4: Extend the dict returned by `build_child_report`**

In `build_child_report`, just before the `return {` statement, add:

```python
    age = child.age if child.age is not None else "—"
    trigger_counts = _count_dist([i.trigger for i in incidents])
    behavior_counts = _count_dist([i.type for i in incidents])
    action_counts = _count_dist([iv.name for i in incidents for iv in i.interventions])
```

Then add these keys inside the returned dict (place them after `"peak_time": peak_time,`):

```python
        "age": age,
        "school_roll": "",
        "trigger_counts": trigger_counts,
        "behavior_counts": behavior_counts,
        "action_counts": action_counts,
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_reports.py -k "count_dist or aggregates or empty" -v`
Expected: all three PASS.

- [ ] **Step 6: Commit**

```bash
git add reports.py tests/test_reports.py
git commit -m "feat: aggregate trigger/behavior/action counts + age in child report"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 3: `reports.py` — rewrite `render_child_report_pdf` (management layout)

**Files:**
- Modify: `reports.py` (replace the whole `render_child_report_pdf` function)
- Modify: `tests/test_reports.py` (update the two render smoke tests)

- [ ] **Step 1: Update the render smoke tests**

In `tests/test_reports.py`, REPLACE `test_render_child_report_pdf_returns_pdf_bytes` and
`test_render_child_report_pdf_empty_state` with:

```python
def test_render_child_report_pdf_returns_pdf_bytes():
    from reports import render_child_report_pdf

    report = {
        "school": "Test School", "school_roll": "12345B", "child_name": "Cian M.",
        "room_name": "Room 1", "key_worker": "Staff Member 1", "age": 8,
        "period_label": "Last 30 days", "period_range": "13 May 2026 – 11 Jun 2026",
        "generated_on": "11 Jun 2026", "total_incidents": 3, "per_week_avg": 0.7,
        "top_severity": "Medium", "avg_duration": "15 min",
        "incident_rows": [{"date": "10 Jun 2026", "type": "Behavioural",
                           "severity": "Medium", "trigger": "Sensory", "outcome": "Resolved"}],
        "top_trigger": "Sensory", "top_type": "Behavioural",
        "peak_time": "Morning (before 12:00)",
        "pattern_text": "Most incidents were Behavioural type.",
        "trigger_counts": [("Sensory", 2), ("Transition", 1)],
        "behavior_counts": [("Behavioural", 2), ("Crisis", 1)],
        "action_counts": [("Calm Space", 2), ("Sensory Tool", 1)],
    }
    out = render_child_report_pdf(report)
    assert isinstance(out, (bytes, bytearray))
    assert out[:4] == b"%PDF"


def test_render_child_report_pdf_empty_state():
    from reports import render_child_report_pdf

    report = {
        "school": "Test School", "school_roll": "", "child_name": "Empty Kid",
        "room_name": "—", "key_worker": "—", "age": "—",
        "period_label": "Last 7 days", "period_range": "05 Jun 2026 – 11 Jun 2026",
        "generated_on": "11 Jun 2026", "total_incidents": 0, "per_week_avg": 0.0,
        "top_severity": "—", "avg_duration": "N/A", "incident_rows": [],
        "top_trigger": "—", "top_type": "—", "peak_time": "—",
        "pattern_text": "No incidents recorded in this period.",
        "trigger_counts": [], "behavior_counts": [], "action_counts": [],
    }
    out = render_child_report_pdf(report)
    assert out[:4] == b"%PDF"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_reports.py -k pdf -v`
Expected: PASS or FAIL depending on the old code, but after Step 3 they must pass. (The old
renderer ignores the new keys; the goal is the rewritten renderer in Step 3.) Proceed to Step 3.

- [ ] **Step 3: Replace `render_child_report_pdf` entirely**

Replace the whole existing `def render_child_report_pdf(report):` function in `reports.py` with:

```python
def render_child_report_pdf(report):
    """Construiește PDF-ul 'management report' în memorie și întoarce bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    footer_left = f"{report['child_name']} · Generated {report['generated_on']}"

    class NumberedCanvas(canvas.Canvas):
        """Desenează 'Page X of Y' + subsol oficial pe fiecare pagină."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved = []

        def showPage(self):
            self._saved.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved)
            for state in self._saved:
                self.__dict__.update(state)
                self._draw_footer(total)
                super().showPage()
            super().save()

        def _draw_footer(self, total):
            self.setFont("Helvetica", 8)
            self.setFillGray(0.5)
            self.drawString(18 * mm, 12 * mm, footer_left)
            self.drawCentredString(A4[0] / 2, 12 * mm, "CONFIDENTIAL")
            self.drawRightString(A4[0] - 18 * mm, 12 * mm,
                                 f"Page {self._pageNumber} of {total}")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title="EDI AI Behaviour Report",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("rh1", parent=styles["Title"], fontName="Helvetica-Bold",
                        fontSize=18, spaceAfter=2)
    sub = ParagraphStyle("rsub", parent=styles["Normal"], fontName="Helvetica",
                         fontSize=9, textColor=colors.grey)
    h2 = ParagraphStyle("rh2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                        fontSize=12, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("rbody", parent=styles["Normal"], fontName="Helvetica", fontSize=10)

    grey_grid = colors.HexColor("#bdbdbd")
    head_bg = colors.HexColor("#e8eef7")

    story = []

    # 1. Header band
    story.append(Paragraph("EDI AI Behaviour Report", h1))
    roll = report.get("school_roll") or ""
    school_line = report["school"]
    if roll:
        school_line += f" · Roll Number: {roll}"
    story.append(Paragraph(f"{school_line} · Generated {report['generated_on']}", sub))
    story.append(Spacer(1, 10))

    # 2. Student Details
    story.append(Paragraph("Student Details", h2))
    details = [
        ["Student", report["child_name"], "Class", report["room_name"]],
        ["Key Worker", report["key_worker"], "Age", str(report["age"])],
        ["Period", f"{report['period_label']} ({report['period_range']})", "", ""],
    ]
    details_tbl = Table(details, colWidths=[26 * mm, 60 * mm, 24 * mm, 44 * mm])
    details_tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (0, -1), head_bg),
        ("BACKGROUND", (2, 0), (2, 1), head_bg),
        ("SPAN", (1, 2), (3, 2)),
        ("GRID", (0, 0), (-1, -1), 0.5, grey_grid),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(details_tbl)
    story.append(Spacer(1, 10))

    # 3. Key Stats
    story.append(Paragraph("Key Stats", h2))
    stats = [
        [str(report["total_incidents"]), str(report["per_week_avg"]),
         report["top_severity"], report["avg_duration"]],
        ["Total Incidents", "Per Week Avg", "Top Severity", "Avg Duration"],
    ]
    stats_tbl = Table(stats, colWidths=[39 * mm] * 4)
    stats_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 15),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, 1), 8),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.5, grey_grid),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stats_tbl)

    # 4. Incident Summary (per-incident)
    story.append(Paragraph("Incident Summary", h2))
    if report["incident_rows"]:
        data = [["Date", "Type", "Severity", "Trigger", "Outcome"]]
        for row in report["incident_rows"]:
            data.append([row["date"], row["type"], row["severity"], row["trigger"], row["outcome"]])
        tbl = Table(data, colWidths=[26 * mm, 34 * mm, 24 * mm, 34 * mm, 36 * mm], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), head_bg),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, grey_grid),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No incidents recorded in this period.", body))

    # 5. Pattern Analysis (aggregated 3-column)
    story.append(Paragraph("Pattern Analysis", h2))
    story.append(Paragraph(report["pattern_text"], body))
    if report["total_incidents"]:
        trig, beh, act = report["trigger_counts"], report["behavior_counts"], report["action_counts"]
        rows_n = max(len(trig), len(beh), len(act), 1)

        def _cell(lst, idx):
            if idx < len(lst):
                label, count = lst[idx]
                return f"{label} ({count})"
            return ""

        pa = [["Triggers", "Behaviors", "Actions Taken"]]
        for idx in range(rows_n):
            pa.append([_cell(trig, idx), _cell(beh, idx), _cell(act, idx)])
        pa_tbl = Table(pa, colWidths=[52 * mm] * 3, repeatRows=1)
        pa_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), head_bg),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, grey_grid),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(Spacer(1, 4))
        story.append(pa_tbl)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
```

- [ ] **Step 4: Run the render tests to verify they pass**

Run: `python -m pytest tests/test_reports.py -k pdf -v`
Expected: both render tests PASS.

- [ ] **Step 5: Run the full report test file**

Run: `python -m pytest tests/test_reports.py -v`
Expected: all PASS (pure aggregation + render + endpoint tests).

- [ ] **Step 6: Commit**

```bash
git add reports.py tests/test_reports.py
git commit -m "feat: management-report PDF layout (student details, 3-col patterns, page footer)"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 4: Endpoint — fill School Name + Roll Number from the DB

**Files:**
- Modify: `reports_api.py`

- [ ] **Step 1: Fill both school fields**

In `reports_api.py`, find:
```python
    report = build_child_report(child, incidents, period, today)
    report["school"] = serialize_system_config(SystemConfig.query.first())["name"]
    pdf = render_child_report_pdf(report)
```
Replace with:
```python
    report = build_child_report(child, incidents, period, today)
    sc = serialize_system_config(SystemConfig.query.first())
    report["school"] = sc["name"]
    report["school_roll"] = sc["roll_number"]
    pdf = render_child_report_pdf(report)
```

- [ ] **Step 2: Run the full suite**

Run: `python -m pytest -q`
Expected: all PASS (the endpoint tests still return valid `%PDF`; nothing else changed).

- [ ] **Step 3: Commit**

```bash
git add reports_api.py
git commit -m "feat: include school roll number in child report header"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 5: Manual regeneration + developer notes

**Files:**
- Modify: `DEVELOPER_NOTES.md`

- [ ] **Step 1: Regenerate and visually verify the PDF**

Run: `python app.py` (open http://127.0.0.1:5000/).
1. Go to **Log Incident** and log 2–3 incidents for one child, choosing different Triggers and
   one or more Interventions each, and a Duration.
2. Go to **Reports** → Report Type **Individual Child** → pick that child → **This Month** →
   **Generate Report**. Open the downloaded PDF and confirm:
   - Header shows the **School Name** and **Roll Number** (from Settings → System).
   - **Student Details** table shows student, class, key worker, age with clear borders.
   - **Pattern Analysis** shows three columns (Triggers / Behaviors / Actions Taken) with real
     counts like `Sensory (2)`.
   - The per-incident **Incident Summary** table is present.
   - The page **footer** shows `Page 1 of 1`, the student name, and the date.
3. Stop the server with Ctrl+C.

Expected: a management-grade PDF as above. If anything is off, fix it before committing notes.

- [ ] **Step 2: Update `DEVELOPER_NOTES.md`**

Find the line:
```
- [x] Generare reală rapoarte PDF: raport Individual Child (ReportLab, pure-Python), `GET /api/reports/child/<id>?period=week|month|term`, download on-the-fly din datele reale de incidente. Class Summary / Whole School rămân fast-follow.
```
Replace with:
```
- [x] Generare reală rapoarte PDF: raport "management" Individual Child (ReportLab, pure-Python) — Student Details, Key Stats, Incident Summary, Pattern Analysis agregat pe 3 coloane (Triggers/Behaviors/Actions Taken), subsol "Page X of Y", antet cu School Name + Roll Number din SystemConfig. `GET /api/reports/child/<id>?period=week|month|term`, download on-the-fly. Class Summary / Whole School rămân fast-follow.
```

- [ ] **Step 3: Commit**

```bash
git add DEVELOPER_NOTES.md
git commit -m "docs: note management-report PDF upgrade"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Done criteria

- `python -m pytest -q` is green (existing suite + updated/new report tests).
- The generated PDF shows: dynamic School Name + Roll Number; bordered Student Details; a
  3-column aggregated Pattern Analysis with real counts; per-incident Incident Summary; a
  "Page X of Y" footer with student name + date on every page; Helvetica with clear grid lines.
- Empty-window reports still render a valid PDF.
- The endpoint, periods, and filename are unchanged from v1.
