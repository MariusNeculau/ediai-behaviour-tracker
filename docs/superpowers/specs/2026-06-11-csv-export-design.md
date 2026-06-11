# CSV Export of Incidents — Design Spec

**Date:** 2026-06-11
**Status:** Approved (pending spec review)

## Problem

Incident data lives in the app's SQLite DB and is only viewable in the dashboard. Staff need to
pull the full incident log into a spreadsheet for their own analysis, archiving, or sharing.

## Goal

A one-click **Export All Incidents (CSV)** action in the Reports tab that downloads every logged
incident as a UTF-8 CSV that opens cleanly in Excel.

## Non-Goals

- Filtering/period selection on export (a full dump; filter in the spreadsheet).
- Excel `.xlsx` output (plain CSV only).
- Import / round-trip.
- Per-child or per-class scoped CSV (the PDF reports already cover scoped views).

## Architecture

### `exports.py` (new) — pure CSV builder

```python
def incidents_to_csv(incidents) -> str:
    """Render incidents (model instances) to a CSV string using the stdlib csv module."""
```
- Uses `csv.writer` over an `io.StringIO`. Reads attributes only (no Flask/DB session), so it is
  unit-testable with lightweight stand-ins.
- Columns (header row + one row per incident, in this order):
  `Date, Time, Child, Class, Type, Severity, Trigger, Duration (min), Interventions, Outcome,
  Key Worker, Status, Description, Notes`.
- Field mapping per incident `i`:
  - `Date` = `i.occurred_at.strftime("%Y-%m-%d")` (empty if `occurred_at` is None).
  - `Time` = `i.occurred_at.strftime("%H:%M")` (empty if None).
  - `Child` = `i.child.name` if `i.child` else `""`.
  - `Class` = `i.child.room.name` if `i.child` and `i.child.room` else `""`.
  - `Type`, `Severity`, `Trigger`, `Outcome`, `Status` = the attribute or `""` if falsy.
  - `Duration (min)` = `i.duration` if not None else `""`.
  - `Interventions` = `"; ".join(iv.name for iv in i.interventions)`.
  - `Key Worker` = `i.staff.name` if `i.staff` else `""`.
  - `Description`, `Notes` = the attribute or `""`.
- Returns the CSV text (no BOM — the endpoint adds the BOM). Empty `incidents` → just the header row.
- Line terminator: pass `lineterminator="\n"` to `csv.writer` for deterministic output.

### `reports_api.py` (modify) — export endpoint

```python
GET /api/export/incidents.csv
```
- `incidents = Incident.query.order_by(Incident.occurred_at.desc()).all()`.
- `csv_text = incidents_to_csv(incidents)`.
- Prepend a UTF-8 BOM so Excel on Windows detects encoding: `body = "﻿" + csv_text`.
- Return `Response(body, mimetype="text/csv",
  headers={"Content-Disposition": f'attachment; filename="EDI_AI_Incidents_{today:%Y%m%d}.csv"'})`
  where `today = date.today()`.
- No parameters, no error cases beyond an empty DB (which yields the header-only CSV).

### `templates/dashboard.html` (modify) — Reports tab button

- In `renderReports()`, add an action below the Generate Report card (before "Recent Reports"):
  ```html
  <div style="margin:0 0 22px">
    <button class="btn-outline" onclick="exportIncidentsCsv()">&#11015; Export All Incidents (CSV)</button>
  </div>
  ```
- Add the handler:
  ```javascript
  function exportIncidentsCsv(){ window.location='/api/export/incidents.csv'; }
  ```
  The browser downloads the file via the attachment Content-Disposition.

## Testing

**`tests/test_exports.py` (new):**

Pure builder (SimpleNamespace stand-ins):
1. `test_incidents_to_csv_header_and_row` — one incident with a child (name + room), two
   interventions, a staff/key worker, a duration; assert the header line is exact and the data
   row contains the child name, class, `"Calm Space; Sensory Tool"`, key worker, and the date.
2. `test_incidents_to_csv_empty` — `incidents_to_csv([])` returns only the header row (one line).
3. `test_incidents_to_csv_handles_missing` — an incident with `child=None`, `staff=None`,
   `duration=None`, `interventions=[]` → those cells are empty strings (no crash).

Endpoint (Flask client; `child_id` fixture exists):
4. `test_export_incidents_csv_download` — `GET /api/export/incidents.csv` → 200,
   `Content-Type` starts with `text/csv`, `Content-Disposition` contains `.csv`, body starts with
   the BOM `﻿` followed by the `Date,Time,Child` header.
5. `test_export_incidents_csv_includes_row` — after adding one `Incident` for the `child_id`
   fixture, the response body contains that incident's date and type.

## Done Criteria

- `python -m pytest -q` green (existing suite + the new export tests).
- The Reports tab has an "Export All Incidents (CSV)" button that downloads
  `EDI_AI_Incidents_<date>.csv` containing every incident, openable in Excel with correct
  accented characters.
- An empty database exports a valid header-only CSV.
