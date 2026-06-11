# Class Summary & Whole School Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real PDF generation for Class Summary (one class) and Whole School (all classes), each with a per-entity breakdown table, reusing the existing aggregation and management-report PDF style.

**Architecture:** Extract a shared `_aggregate` helper in `reports.py`, refactor `build_child_report` to use it, and add `build_class_report`/`build_school_report`. Generalize the renderer to `render_report_pdf(report)` that branches on `report["report_type"]` while sharing header/stats/pattern/footer. Two new blueprint routes serve the PDFs; the Reports tab wires the two types with a class selector.

**Tech Stack:** Python, ReportLab, Flask, pytest, vanilla JS.

---

## File Structure

- `reports.py` (modify) — add `_aggregate`; refactor `build_child_report`; add `build_class_report`, `build_school_report`; rename/generalize `render_child_report_pdf` → `render_report_pdf`.
- `reports_api.py` (modify) — `_window_bounds` helper; child route uses it + `render_report_pdf`; add `class_report` and `school_report` routes.
- `tests/test_reports.py` (modify) — pure builder tests, render smoke tests, endpoint tests.
- `templates/dashboard.html` (modify) — `toggleReportInputs`, class selector, extended `generateReport`.
- `DEVELOPER_NOTES.md` (modify) — note the two new report types.

---

## Task 1: Confirm baseline

- [ ] **Step 1: Run the suite**

Run: `python -m pytest -q`
Expected: all PASS (46). No schema change; no DB reset needed.

---

## Task 2: `reports.py` — extract `_aggregate`, refactor `build_child_report`

**Files:** Modify `reports.py`, `tests/test_reports.py`.

- [ ] **Step 1: Add the `_aggregate` regression test**

Append to `tests/test_reports.py`:

```python
def test_aggregate_shared():
    from reports import _aggregate

    incs = [
        SimpleNamespace(severity="High", duration=10, trigger="Sensory", type="Behavioural",
                        interventions=[], occurred_at=datetime(2026, 6, 10, 9, 0)),
        SimpleNamespace(severity="Medium", duration=None, trigger="Sensory", type="Crisis",
                        interventions=[], occurred_at=datetime(2026, 6, 9, 14, 0)),
    ]
    a = _aggregate(incs, 30)
    assert a["total_incidents"] == 2
    assert a["per_week_avg"] == 0.5
    assert a["top_trigger"] == "Sensory"
    assert a["avg_duration"] == "10 min"
    assert a["pattern_text"].startswith("Most incidents were")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_reports.py::test_aggregate_shared -v`
Expected: FAIL — `ImportError` (`_aggregate` does not exist).

- [ ] **Step 3: Add `_aggregate` to `reports.py`**

Add this function directly ABOVE `build_child_report`:

```python
def _aggregate(incidents, window_days):
    """Statistici partajate de toate tipurile de raport (copil/clasă/școală)."""
    total = len(incidents)
    per_week_avg = round(total / (window_days / 7.0), 1)
    top_severity = _mode([i.severity for i in incidents])
    durations = [i.duration for i in incidents if i.duration is not None]
    avg_duration = f"{round(sum(durations) / len(durations))} min" if durations else "N/A"
    trigger_counts = _count_dist([i.trigger for i in incidents])
    behavior_counts = _count_dist([i.type for i in incidents])
    action_counts = _count_dist([iv.name for i in incidents for iv in i.interventions])
    peak_time = _peak_time(incidents)
    top_trigger = _mode([i.trigger for i in incidents])
    top_type = _mode([i.type for i in incidents])

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
        "total_incidents": total,
        "per_week_avg": per_week_avg,
        "top_severity": top_severity,
        "avg_duration": avg_duration,
        "trigger_counts": trigger_counts,
        "behavior_counts": behavior_counts,
        "action_counts": action_counts,
        "peak_time": peak_time,
        "top_trigger": top_trigger,
        "top_type": top_type,
        "pattern_text": pattern_text,
    }
```

- [ ] **Step 4: Refactor `build_child_report` to use `_aggregate`**

Replace the ENTIRE existing `build_child_report` function body with:

```python
def build_child_report(child, incidents, period, today):
    """View-model pur (dict) pentru raportul unui copil. `school` e completat de endpoint."""
    window_days = _WINDOW_DAYS[period]
    start = today - timedelta(days=window_days - 1)
    agg = _aggregate(incidents, window_days)

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
    age = child.age if child.age is not None else "—"

    return {
        "report_type": "child",
        "school": "",
        "school_roll": "",
        "child_name": child.name,
        "room_name": child.room.name if child.room else "—",
        "key_worker": child.key_worker.name if child.key_worker else "—",
        "age": age,
        "period_label": _PERIOD_LABEL[period],
        "period_range": f"{start.strftime('%d %b %Y')} – {today.strftime('%d %b %Y')}",
        "generated_on": today.strftime("%d %b %Y"),
        "incident_rows": rows,
        **agg,
    }
```

- [ ] **Step 5: Run the child + aggregate tests**

Run: `python -m pytest tests/test_reports.py -k "aggregate or build_child or pdf or report" -v`
Expected: all PASS — the existing child aggregate/empty/render tests (regression gate) plus the new
`test_aggregate_shared`. Then `python -m pytest -q` → all green (47).

- [ ] **Step 6: Commit**

```bash
git add reports.py tests/test_reports.py
git commit -m "refactor: extract _aggregate; build_child_report reuses it (+report_type)"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 3: `reports.py` — `build_class_report` + `build_school_report`

**Files:** Modify `reports.py`, `tests/test_reports.py`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_reports.py`:

```python
def _mk_inc(child_id, trigger, hour=9, typ="Behavioural", sev="Medium", dur=10):
    return SimpleNamespace(
        child_id=child_id, occurred_at=datetime(2026, 6, 10, hour, 0),
        type=typ, severity=sev, trigger=trigger, outcome="Resolved", duration=dur,
        interventions=[SimpleNamespace(name="Calm Space")],
    )


def test_build_class_report():
    from reports import build_class_report

    room = SimpleNamespace(id=1, name="Room 1")
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1),
            SimpleNamespace(id=11, name="Bob", room_id=1)]
    incidents = [_mk_inc(10, "Sensory"), _mk_inc(10, "Sensory"), _mk_inc(11, "Noise")]
    r = build_class_report(room, kids, incidents, "month", date(2026, 6, 11))

    assert r["report_type"] == "class"
    assert r["subtitle"] == "Class Summary · Room 1"
    assert ["Students", "2"] in r["details_rows"]
    assert r["total_incidents"] == 3
    assert r["breakdown_header"] == ["Student", "Incidents", "Top Trigger"]
    assert r["breakdown_rows"][0] == ["Alice", "2", "Sensory"]
    assert r["breakdown_rows"][1] == ["Bob", "1", "Noise"]


def test_build_class_report_empty():
    from reports import build_class_report

    room = SimpleNamespace(id=1, name="Room 1")
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1)]
    r = build_class_report(room, kids, [], "week", date(2026, 6, 11))

    assert r["total_incidents"] == 0
    assert r["breakdown_rows"] == [["Alice", "0", "—"]]
    assert r["pattern_text"] == "No incidents recorded in this period."


def test_build_school_report():
    from reports import build_school_report

    rooms = [SimpleNamespace(id=1, name="Room 1"), SimpleNamespace(id=2, name="Room 2")]
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1),
            SimpleNamespace(id=11, name="Bob", room_id=2),
            SimpleNamespace(id=12, name="Cara", room_id=2)]
    incidents = [_mk_inc(11, "Noise"), _mk_inc(12, "Noise"), _mk_inc(10, "Sensory")]
    r = build_school_report(rooms, kids, incidents, "term", date(2026, 6, 11))

    assert r["report_type"] == "school"
    assert ["Classes", "2"] in r["details_rows"]
    assert ["Students", "3"] in r["details_rows"]
    assert r["total_incidents"] == 3
    assert r["breakdown_header"] == ["Class", "Students", "Incidents", "Top Trigger"]
    assert r["breakdown_rows"][0] == ["Room 2", "2", "2", "Noise"]
    assert r["breakdown_rows"][1] == ["Room 1", "1", "1", "Sensory"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_reports.py -k "class_report or school_report" -v`
Expected: FAIL — `ImportError` (the two builders don't exist).

- [ ] **Step 3: Add the two builders to `reports.py`**

Add these functions directly BELOW `build_child_report`:

```python
def build_class_report(room, children, incidents, period, today):
    """View-model pur pentru un raport de clasă (agregate + breakdown per-elev)."""
    window_days = _WINDOW_DAYS[period]
    start = today - timedelta(days=window_days - 1)
    period_range = f"{start.strftime('%d %b %Y')} – {today.strftime('%d %b %Y')}"
    agg = _aggregate(incidents, window_days)

    breakdown = []
    for c in children:
        c_inc = [i for i in incidents if i.child_id == c.id]
        breakdown.append([c.name, str(len(c_inc)), _mode([i.trigger for i in c_inc])])
    breakdown.sort(key=lambda row: (-int(row[1]), row[0]))

    return {
        "report_type": "class",
        "school": "",
        "school_roll": "",
        "subtitle": f"Class Summary · {room.name}",
        "period_label": _PERIOD_LABEL[period],
        "period_range": period_range,
        "generated_on": today.strftime("%d %b %Y"),
        "details_title": "Class Details",
        "details_rows": [
            ["Class", room.name],
            ["Students", str(len(children))],
            ["Period", f"{_PERIOD_LABEL[period]} ({period_range})"],
        ],
        "breakdown_title": "Students",
        "breakdown_header": ["Student", "Incidents", "Top Trigger"],
        "breakdown_rows": breakdown,
        **agg,
    }


def build_school_report(rooms, children, incidents, period, today):
    """View-model pur pentru un raport pe toată școala (agregate + breakdown per-clasă)."""
    window_days = _WINDOW_DAYS[period]
    start = today - timedelta(days=window_days - 1)
    period_range = f"{start.strftime('%d %b %Y')} – {today.strftime('%d %b %Y')}"
    agg = _aggregate(incidents, window_days)

    by_room = {}
    for c in children:
        by_room.setdefault(c.room_id, set()).add(c.id)

    breakdown = []
    for room in rooms:
        ids = by_room.get(room.id, set())
        r_inc = [i for i in incidents if i.child_id in ids]
        breakdown.append([room.name, str(len(ids)), str(len(r_inc)),
                          _mode([i.trigger for i in r_inc])])
    breakdown.sort(key=lambda row: (-int(row[2]), row[0]))

    return {
        "report_type": "school",
        "school": "",
        "school_roll": "",
        "subtitle": "Whole School Summary",
        "period_label": _PERIOD_LABEL[period],
        "period_range": period_range,
        "generated_on": today.strftime("%d %b %Y"),
        "details_title": "School Overview",
        "details_rows": [
            ["Classes", str(len(rooms))],
            ["Students", str(len(children))],
            ["Period", f"{_PERIOD_LABEL[period]} ({period_range})"],
        ],
        "breakdown_title": "Classes",
        "breakdown_header": ["Class", "Students", "Incidents", "Top Trigger"],
        "breakdown_rows": breakdown,
        **agg,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_reports.py -k "class_report or school_report" -v`
Expected: all three PASS.

- [ ] **Step 5: Commit**

```bash
git add reports.py tests/test_reports.py
git commit -m "feat: add build_class_report and build_school_report aggregations"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 4: `reports.py` — generalize the renderer to `render_report_pdf`

**Files:** Modify `reports.py`, `tests/test_reports.py`.

- [ ] **Step 1: Add render smoke tests for class & school**

Append to `tests/test_reports.py`:

```python
def test_render_class_report_pdf():
    from reports import build_class_report, render_report_pdf

    room = SimpleNamespace(id=1, name="Room 1")
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1)]
    incs = [_mk_inc(10, "Sensory")]
    rep = build_class_report(room, kids, incs, "month", date(2026, 6, 11))
    rep["school"] = "Test School"
    rep["school_roll"] = "12345B"
    out = render_report_pdf(rep)
    assert out[:4] == b"%PDF"


def test_render_school_report_pdf():
    from reports import build_school_report, render_report_pdf

    rooms = [SimpleNamespace(id=1, name="Room 1"), SimpleNamespace(id=2, name="Room 2")]
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1)]
    rep = build_school_report(rooms, kids, [], "week", date(2026, 6, 11))
    rep["school"] = "Test School"
    rep["school_roll"] = ""
    out = render_report_pdf(rep)
    assert out[:4] == b"%PDF"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_reports.py -k "render_class or render_school" -v`
Expected: FAIL — `ImportError` (`render_report_pdf` does not exist yet).

- [ ] **Step 3: Replace `render_child_report_pdf` with `render_report_pdf`**

Replace the WHOLE existing `def render_child_report_pdf(report):` function with the following
`render_report_pdf` (keep ReportLab imports inside the function; keep UTF-8 chars). At the very end
of the file (after the function) add the back-compat alias line shown below.

```python
def render_report_pdf(report):
    """Construiește un PDF de raport (copil/clasă/școală) și întoarce bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    footer_left = "Confidential - EDI AI Report"

    class NumberedCanvas(canvas.Canvas):
        """Desenează subsolul + 'Page X of Y' pe fiecare pagină."""

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
                        fontSize=18, spaceAfter=2, alignment=1)
    school_style = ParagraphStyle("rschool", parent=styles["Normal"], fontName="Helvetica-Bold",
                                  fontSize=11, alignment=1)
    subtitle_style = ParagraphStyle("rsubtitle", parent=styles["Normal"], fontName="Helvetica-Bold",
                                    fontSize=11, alignment=1, textColor=colors.HexColor("#33475b"))
    sub = ParagraphStyle("rsub", parent=styles["Normal"], fontName="Helvetica",
                         fontSize=9, textColor=colors.grey, alignment=1)
    h2 = ParagraphStyle("rh2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                        fontSize=12, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("rbody", parent=styles["Normal"], fontName="Helvetica", fontSize=10)

    grey_grid = colors.HexColor("#bdbdbd")
    head_bg = colors.HexColor("#e8eef7")
    box_border = colors.HexColor("#7a7a7a")
    rtype = report.get("report_type", "child")

    story = []

    # 1. Header band (centered, bold school identity)
    story.append(Paragraph("EDI AI Behaviour Report", h1))
    roll = report.get("school_roll") or ""
    school_line = report["school"]
    if roll:
        school_line += f" · Roll Number: {roll}"
    story.append(Paragraph(school_line, school_style))
    if report.get("subtitle"):
        story.append(Paragraph(report["subtitle"], subtitle_style))
    story.append(Paragraph(f"Generated {report['generated_on']}", sub))
    story.append(Spacer(1, 12))

    # 2. Details (child = Student Details 4-col; class/school = generic 2-col)
    if rtype == "child":
        story.append(Paragraph("Student Details", h2))
        details = [
            ["Student", report["child_name"], "Class", report["room_name"]],
            ["Key Worker", report["key_worker"], "Age", str(report["age"])],
            ["Period", f"{report['period_label']} ({report['period_range']})", "", ""],
        ]
        details_tbl = Table(details, colWidths=[26 * mm, 60 * mm, 24 * mm, 44 * mm])
        details_tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (0, -1), head_bg),
            ("BACKGROUND", (2, 0), (2, 1), head_bg),
            ("SPAN", (1, 2), (3, 2)),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, grey_grid),
            ("BOX", (0, 0), (-1, -1), 1.0, box_border),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(details_tbl)
    else:
        story.append(Paragraph(report["details_title"], h2))
        details = [[label, value] for label, value in report["details_rows"]]
        details_tbl = Table(details, colWidths=[40 * mm, 134 * mm])
        details_tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (0, -1), head_bg),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, grey_grid),
            ("BOX", (0, 0), (-1, -1), 1.0, box_border),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(details_tbl)
    story.append(Spacer(1, 12))

    # 3. Key Stats (shared)
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
        ("INNERGRID", (0, 0), (-1, -1), 0.5, grey_grid),
        ("BOX", (0, 0), (-1, -1), 1.0, box_border),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stats_tbl)
    story.append(Spacer(1, 12))

    # 4. Middle table (child = Incident Summary; class/school = breakdown)
    if rtype == "child":
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
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, grey_grid),
                ("BOX", (0, 0), (-1, -1), 1.0, box_border),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(tbl)
        else:
            story.append(Paragraph("No incidents recorded in this period.", body))
    else:
        story.append(Paragraph(report["breakdown_title"], h2))
        header = report["breakdown_header"]
        if report["breakdown_rows"]:
            data = [header] + report["breakdown_rows"]
            col_w = [70 * mm, 40 * mm, 64 * mm] if len(header) == 3 \
                else [60 * mm, 30 * mm, 34 * mm, 50 * mm]
            bt = Table(data, colWidths=col_w, repeatRows=1)
            bt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), head_bg),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, grey_grid),
                ("BOX", (0, 0), (-1, -1), 1.0, box_border),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(bt)
        else:
            story.append(Paragraph("No data for this period.", body))
    story.append(Spacer(1, 12))

    # 5. Pattern Analysis (shared, aggregated 3-column)
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
        pa_tbl = Table(pa, colWidths=[58 * mm] * 3, repeatRows=1)
        pa_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), head_bg),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, grey_grid),
            ("BOX", (0, 0), (-1, -1), 1.0, box_border),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(Spacer(1, 6))
        story.append(pa_tbl)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


# Back-compat: vechiul nume folosit înainte de generalizare.
render_child_report_pdf = render_report_pdf
```

- [ ] **Step 4: Run the render + full report tests**

Run: `python -m pytest tests/test_reports.py -v`
Expected: all PASS — child render tests (unchanged output) + the new class/school render smoke tests.

- [ ] **Step 5: Commit**

```bash
git add reports.py tests/test_reports.py
git commit -m "feat: generalize PDF renderer to render_report_pdf (child/class/school)"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 5: `reports_api.py` — class & school endpoints

**Files:** Modify `reports_api.py`, `tests/test_reports.py`.

- [ ] **Step 1: Write the failing endpoint tests**

Append to `tests/test_reports.py`:

```python
def test_class_report_pdf_download(client, room_id):
    res = client.get(f"/api/reports/class/{room_id}?period=month")
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert res.data[:4] == b"%PDF"
    cd = res.headers["Content-Disposition"]
    assert "Class" in cd and ".pdf" in cd


def test_class_report_unknown_room_returns_404(client):
    res = client.get("/api/reports/class/99999?period=month")
    assert res.status_code == 404


def test_class_report_invalid_period_returns_400(client, room_id):
    res = client.get(f"/api/reports/class/{room_id}?period=decade")
    assert res.status_code == 400


def test_school_report_pdf_download(client):
    res = client.get("/api/reports/school?period=term")
    assert res.status_code == 200
    assert res.data[:4] == b"%PDF"
    assert "Whole_School" in res.headers["Content-Disposition"]


def test_school_report_invalid_period_returns_400(client):
    res = client.get("/api/reports/school?period=nope")
    assert res.status_code == 400
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_reports.py -k "class_report_pdf or class_report_unknown or class_report_invalid or school_report" -v`
Expected: FAIL — `404 Not Found` (routes don't exist yet).

- [ ] **Step 3: Update `reports_api.py` imports and add a window helper**

Replace the imports block at the top of `reports_api.py`:
```python
from models import db, Child, Incident, SystemConfig
from serializers import serialize_system_config
from reports import period_start, build_child_report, render_child_report_pdf
```
with:
```python
from models import db, Child, Incident, Room, SystemConfig
from serializers import serialize_system_config
from reports import (
    period_start, build_child_report, build_class_report, build_school_report,
    render_report_pdf,
)
```

Add this helper directly after the `reports_bp = Blueprint(...)` line:
```python
def _window_bounds(period, today):
    """(start_dt, end_dt) pentru fereastra rolling; ridică ValueError la period invalid."""
    start = period_start(period, today)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())
    return start_dt, end_dt
```

- [ ] **Step 4: Refactor the existing child route to use the helper + new render name**

In `child_report`, replace this block:
```python
    period = request.args.get("period", "month")
    today = date.today()
    try:
        start = period_start(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())
    incidents = (
```
with:
```python
    period = request.args.get("period", "month")
    today = date.today()
    try:
        start_dt, end_dt = _window_bounds(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    incidents = (
```
and change the render call `pdf = render_child_report_pdf(report)` to `pdf = render_report_pdf(report)`.

- [ ] **Step 5: Add the class and school routes**

Append to the end of `reports_api.py`:
```python
@reports_bp.route("/reports/class/<int:room_id>", methods=["GET"])
def class_report(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Unknown class"}), 404

    period = request.args.get("period", "month")
    today = date.today()
    try:
        start_dt, end_dt = _window_bounds(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    children = Child.query.filter_by(room_id=room_id, active=True).all()
    child_ids = [c.id for c in children]
    incidents = (
        Incident.query
        .filter(Incident.child_id.in_(child_ids),
                Incident.occurred_at >= start_dt,
                Incident.occurred_at < end_dt)
        .all()
    ) if child_ids else []

    report = build_class_report(room, children, incidents, period, today)
    sc = serialize_system_config(SystemConfig.query.first())
    report["school"] = sc["name"]
    report["school_roll"] = sc["roll_number"]
    pdf = render_report_pdf(report)

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", room.name).strip("_") or "class"
    filename = f"EDI_AI_Report_Class_{safe_name}_{period}_{today:%Y%m%d}.pdf"
    return Response(
        pdf, mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@reports_bp.route("/reports/school", methods=["GET"])
def school_report():
    period = request.args.get("period", "month")
    today = date.today()
    try:
        start_dt, end_dt = _window_bounds(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    rooms = Room.query.filter_by(active=True).order_by(Room.name).all()
    children = Child.query.filter_by(active=True).all()
    child_ids = [c.id for c in children]
    incidents = (
        Incident.query
        .filter(Incident.child_id.in_(child_ids),
                Incident.occurred_at >= start_dt,
                Incident.occurred_at < end_dt)
        .all()
    ) if child_ids else []

    report = build_school_report(rooms, children, incidents, period, today)
    sc = serialize_system_config(SystemConfig.query.first())
    report["school"] = sc["name"]
    report["school_roll"] = sc["roll_number"]
    pdf = render_report_pdf(report)

    filename = f"EDI_AI_Report_Whole_School_{period}_{today:%Y%m%d}.pdf"
    return Response(
        pdf, mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 6: Run the endpoint tests, then the full suite**

Run: `python -m pytest tests/test_reports.py -v` → all PASS.
Run: `python -m pytest -q` → all green.

- [ ] **Step 7: Commit**

```bash
git add reports_api.py tests/test_reports.py
git commit -m "feat: add /api/reports/class/<id> and /api/reports/school PDF endpoints"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 6: Frontend — wire Class Summary & Whole School

**Files:** Modify `templates/dashboard.html`.

- [ ] **Step 1: Rename the type `onchange` handler**

Find:
```html
        <select id="r-type" onchange="toggleReportChild()">
```
Replace with:
```html
        <select id="r-type" onchange="toggleReportInputs()">
```

- [ ] **Step 2: Add a class options var and a class selector**

In `renderReports()`, find:
```javascript
  const childOpts=CHILDREN.map(c=>`<option value="${c.id}">${c.name}</option>`).join('')||'<option value="">No children added yet</option>';
```
Add immediately after it:
```javascript
  const classOpts=ROOMS.map(r=>`<option value="${r.id}">${r.name}</option>`).join('')||'<option value="">No classes yet</option>';
```

Then find:
```javascript
      <div class="form-group" id="r-child-wrap">
        <label>Child</label>
        <select id="r-child">${childOpts}</select>
      </div>
```
Add immediately after that block:
```javascript
      <div class="form-group" id="r-class-wrap" style="display:none">
        <label>Class</label>
        <select id="r-class">${classOpts}</select>
      </div>
```

- [ ] **Step 3: Replace `toggleReportChild` with `toggleReportInputs`**

Find:
```javascript
function toggleReportChild(){
  const t=document.getElementById('r-type').value;
  const w=document.getElementById('r-child-wrap');
  if(w) w.style.display=t==='Individual Child'?'flex':'none';
}
```
Replace with:
```javascript
function toggleReportInputs(){
  const t=document.getElementById('r-type').value;
  const cw=document.getElementById('r-child-wrap');
  const kw=document.getElementById('r-class-wrap');
  if(cw) cw.style.display=t==='Individual Child'?'flex':'none';
  if(kw) kw.style.display=t==='Class Summary'?'flex':'none';
}
```

- [ ] **Step 4: Extend `generateReport()`**

Find:
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
Replace with:
```javascript
function generateReport(){
  const type=document.getElementById('r-type').value;
  const periodMap={'This Week':'week','This Month':'month','This Term':'term'};
  const period=periodMap[document.getElementById('r-period').value]||'month';
  if(type==='Individual Child'){
    const id=document.getElementById('r-child').value;
    if(!id){alert('Please select a child.');return;}
    window.location='/api/reports/child/'+id+'?period='+period;
  }else if(type==='Class Summary'){
    const rid=document.getElementById('r-class').value;
    if(!rid){alert('Please select a class.');return;}
    window.location='/api/reports/class/'+rid+'?period='+period;
  }else{
    window.location='/api/reports/school?period='+period;
  }
}
```

- [ ] **Step 5: Verify the template still renders**

Run: `python -m pytest tests/test_settings.py::test_dashboard_reflects_system_config -v`
Expected: PASS.

- [ ] **Step 6: Manual browser check**

Run: `python app.py` (open http://127.0.0.1:5000/). Ensure a class has students with incidents.
Reports →
1. **Class Summary** → pick a class → Generate → a PDF downloads with a per-student breakdown
   (`Student · Incidents · Top Trigger`), Class Details, Key Stats, Pattern Analysis.
2. **Whole School** → Generate → a PDF with a per-class breakdown
   (`Class · Students · Incidents · Top Trigger`).
3. **Individual Child** → still works as before.
Stop the server with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: wire Class Summary and Whole School report downloads"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 7: Developer notes

**Files:** Modify `DEVELOPER_NOTES.md`.

- [ ] **Step 1: Update the PDF reports line**

Find the text `Class Summary / Whole School rămân fast-follow.` at the end of the PDF reports
bullet and replace that trailing sentence with:
```
Include și Class Summary (`/api/reports/class/<room_id>`, breakdown per-elev) și Whole School (`/api/reports/school`, breakdown per-clasă).
```

- [ ] **Step 2: Commit**

```bash
git add DEVELOPER_NOTES.md
git commit -m "docs: note Class Summary & Whole School reports done"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Done criteria

- `python -m pytest -q` green (existing suite + new class/school pure, render, and endpoint tests; child tests unchanged).
- Class Summary and Whole School download real PDFs with a per-entity breakdown table plus shared Key Stats and Pattern Analysis, in the management style.
- The Individual Child report is unchanged.
- Empty class / zero-incident windows still render a valid PDF.
