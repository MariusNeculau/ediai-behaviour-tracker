# Class Summary & Whole School Reports — Design Spec

**Date:** 2026-06-11
**Status:** Approved (pending spec review)
**Builds on:** the management child report (`reports.py`, `reports_api.py`).

## Problem

The Reports tab offers three types — Individual Child, Class Summary, Whole School — but only
Individual Child generates a PDF; the other two show a "not yet implemented" toast. Management
needs aggregate reports across a class and across the whole school.

## Goal

Add real PDF generation for **Class Summary** (all active children in one class) and **Whole
School** (all active children), reusing the existing aggregation + PDF style. Each adds a
per-entity breakdown table (`Name · Incidents · Top Trigger`). The Individual Child report stays
visually identical.

## Non-Goals

- Persisting reports / Recent Reports list (still on-the-fly download).
- Charts/graphs (tables only).
- Changing periods (rolling week/month/term) or the child report's layout.
- Per-incident detail tables in the class/school reports (they use breakdowns instead, since a
  class/school incident list could be very long).

## Data Mapping

Same window + sources as the child report. The breakdown tables:

| Report | Breakdown row |
|--------|---------------|
| Class Summary | `Student · Incidents · Top Trigger` (one row per active child in the class) |
| Whole School | `Class · Students · Incidents · Top Trigger` (one row per active class) |

`Top Trigger` is the mode of `incident.trigger` for that entity (`"—"` if none). Breakdown rows
are sorted by incident count descending, then name ascending. All active entities appear, even
with zero incidents.

## Architecture

### `reports.py` — extract shared aggregation, add two builders

**Refactor (DRY):** extract the shared statistic block into
```python
def _aggregate(incidents, window_days):
    """Shared stats: total_incidents, per_week_avg, top_severity, avg_duration,
    trigger_counts, behavior_counts, action_counts, peak_time, top_trigger, top_type,
    pattern_text. Returns a dict of those keys."""
```
`build_child_report` is refactored to call `_aggregate` and merge the result, keeping its
returned keys byte-for-byte identical (the existing child tests are the regression gate). It
also gains `"report_type": "child"`.

**New pure builders** (no Flask/DB session; read attributes only):
```python
def build_class_report(room, children, incidents, period, today): ...
def build_school_report(rooms, children, incidents, period, today): ...
```
Both return a dict containing: `_aggregate(...)` stats, plus
- `"report_type"`: `"class"` / `"school"`.
- `"school"`, `"school_roll"`: `""` (filled by the endpoint).
- `"subtitle"`: `f"Class Summary · {room.name}"` / `"Whole School Summary"`.
- `"generated_on"`, `"period_label"`, `"period_range"`.
- `"details_title"`: `"Class Details"` / `"School Overview"`.
- `"details_rows"`: list of `[label, value]` pairs:
  - class: `["Class", room.name]`, `["Students", str(n_children)]`, `["Period", "<label> (<range>)"]`.
  - school: `["Classes", str(n_rooms)]`, `["Students", str(n_children)]`, `["Period", "..."]`.
- `"breakdown_title"`: `"Students"` / `"Classes"`.
- `"breakdown_header"`: `["Student", "Incidents", "Top Trigger"]` / `["Class", "Students", "Incidents", "Top Trigger"]`.
- `"breakdown_rows"`: list of lists (cells as strings), sorted as above.

**Class breakdown:** for each child, `n = #incidents with child_id == child.id`,
`top_trigger = _mode([i.trigger for those incidents])`; row `[child.name, str(n), top_trigger]`.

**School breakdown:** group children by `room_id`; for each active room,
`n_students = #children in room`, `n_inc = #incidents whose child is in that room`,
`top_trigger = _mode(...)`; row `[room.name, str(n_students), str(n_inc), top_trigger]`.

### `reports.py` — generalize the renderer

Rename `render_child_report_pdf` → `render_report_pdf(report)` and branch on `report["report_type"]`
for the middle section, sharing the header band, Key Stats table, Pattern Analysis table, and the
`NumberedCanvas` footer across all three types:
- Header band: title + centered/bold school line + `report.get("subtitle")` line (the child report
  sets no subtitle, so its header is unchanged) + generated date.
- `report_type == "child"`: the existing Student Details (4-col) + Incident Summary table (unchanged).
- otherwise: a generic **Details** table from `details_rows` (2-col, bold label column, BOX +
  INNERGRID), then a **breakdown** table from `breakdown_header` + `breakdown_rows` (bold header
  row, BOX + INNERGRID, left-aligned, font 10).
- Then (all types): Key Stats, Pattern Analysis (3-col), footer.

A thin `render_child_report_pdf = render_report_pdf` alias is kept so nothing else breaks, or the
child endpoint is updated to call `render_report_pdf` directly.

### `reports_api.py` — two new endpoints

```python
GET /api/reports/class/<int:room_id>?period=week|month|term
GET /api/reports/school?period=week|month|term
```
- Validate period via `period_start` (→ 400 `{"error": "Invalid period"}` on failure).
- **class:** `room = db.session.get(Room, room_id)`; `None` → 404 `{"error": "Unknown class"}`.
  `children = Child.query.filter_by(room_id=room_id, active=True).all()`;
  `incidents = Incident.query.filter(Incident.child_id.in_([c.id for c in children]),
  occurred_at in window).all()` (empty `children` → no incidents).
  `report = build_class_report(room, children, incidents, period, today)`.
  Filename `EDI_AI_Report_Class_<SafeRoom>_<period>_<date>.pdf`.
- **school:** `rooms = Room.query.filter_by(active=True).order_by(Room.name).all()`;
  `children = Child.query.filter_by(active=True).all()`;
  `incidents = Incident.query.filter(Incident.child_id.in_([c.id for c in children]),
  occurred_at in window).all()`.
  `report = build_school_report(rooms, children, incidents, period, today)`.
  Filename `EDI_AI_Report_Whole_School_<period>_<date>.pdf`.
- Both fill `report["school"]` + `report["school_roll"]` from `SystemConfig`, render with
  `render_report_pdf`, and return the PDF as an attachment (same Response shape as the child route).
- The window filter reuses the child route's convention: `occurred_at >= start 00:00` and
  `occurred_at < (today+1) 00:00`. Factor a small local helper to avoid repeating it three times.

### `templates/dashboard.html` — wire the two types

- Rename `toggleReportChild()` → `toggleReportInputs()` (update the `r-type` `onchange`): show the
  child selector only for Individual Child, and a new class selector (`#r-class-wrap`) only for
  Class Summary.
- Add a class `<select id="r-class">` populated from the existing `ROOMS` global
  (`<option value="${r.id}">${r.name}</option>`), inside `#r-class-wrap` (hidden by default).
- Extend `generateReport()`:
  - Individual Child → `/api/reports/child/<id>?period=` (unchanged; needs a child selected).
  - Class Summary → require a class selected → `/api/reports/class/<roomId>?period=`.
  - Whole School → `/api/reports/school?period=` (no selector).

## Testing (`tests/test_reports.py`)

Pure builders (SimpleNamespace stand-ins; children have `id`, `name`, `room_id`; incidents have
`child_id`, `trigger`, `type`, `severity`, `duration`, `interventions`, `occurred_at`):
1. `test_build_class_report` — 2 children, a known incident set; assert `report_type=="class"`,
   `subtitle`, `details_rows` (Class/Students/Period), shared stats, and `breakdown_rows` ordered
   by incident count desc then name, each `[name, count, top_trigger]`.
2. `test_build_class_report_empty` — class with children but no incidents → `total_incidents==0`,
   every breakdown row shows `0` incidents and `"—"` trigger, `pattern_text` empty-state.
3. `test_build_school_report` — 2 rooms, children split across them, a known incident set; assert
   `report_type=="school"`, `details_rows` (Classes/Students/Period), and per-class `breakdown_rows`
   `[class, students, incidents, top_trigger]` ordered by incidents desc then name.
4. `test_aggregate_shared` — `_aggregate` returns correct totals on a small incident list (locks
   the extracted helper).

Render smoke (valid `%PDF`):
5. `test_render_class_report_pdf` — a class report dict renders to `b"%PDF"`.
6. `test_render_school_report_pdf` — a school report dict renders to `b"%PDF"`.
7. Existing child render/aggregate tests stay green (regression gate for the refactor).

Endpoints (Flask client; `room_id`, `child_id` fixtures exist in conftest):
8. `test_class_report_pdf_download` — `GET /api/reports/class/<room_id>?period=month` → 200,
   `application/pdf`, body `%PDF`, `Content-Disposition` contains `Class` + `.pdf`.
9. `test_class_report_unknown_room_returns_404`.
10. `test_class_report_invalid_period_returns_400`.
11. `test_school_report_pdf_download` — `GET /api/reports/school?period=term` → 200 + `%PDF`,
    filename contains `Whole_School`.
12. `test_school_report_invalid_period_returns_400`.

## Manual Verification

Run `python app.py`; ensure a class has students with logged incidents. Reports →
**Class Summary** → pick a class → Generate (PDF lists per-student breakdown + class aggregates);
**Whole School** → Generate (PDF lists per-class breakdown + school aggregates). Confirm header
school name/roll, "Page X of Y" footer, and breakdown ordering.

## Done Criteria

- `python -m pytest -q` green (existing suite + new class/school tests; child tests unchanged).
- Class Summary and Whole School each download a real PDF with a per-entity breakdown table plus
  shared Key Stats and Pattern Analysis, in the same management style.
- The Individual Child report is unchanged (visually and in its tests).
- Empty class / zero-incident windows still render a valid PDF.
