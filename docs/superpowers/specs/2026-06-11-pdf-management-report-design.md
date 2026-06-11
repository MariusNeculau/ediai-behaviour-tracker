# PDF Management Report (Individual Child v2) — Design Spec

**Date:** 2026-06-11
**Status:** Approved (pending spec review)
**Builds on:** `2026-06-11-pdf-reports-design.md` (the working v1 report).

## Problem

The v1 child PDF is functional but basic: a flat meta line, a single narrative
"Pattern Analysis" paragraph, and no page footer. The user wants a "Management Report":
a bordered Student Details block, a real aggregated Pattern Analysis (counts), an official
"Page X of Y" footer, and a header that pulls School Name + Roll Number from the DB.

## Goal

Refactor the existing `render_child_report_pdf` (and extend `build_child_report`) to produce
a management-grade PDF, keeping the v1 endpoint and download flow unchanged. No new files.

## Non-Goals

- Class Summary / Whole School reports (still fast-follow).
- Persisting reports / Recent Reports list.
- Charts/graphs (counts are presented as tables, not plots).
- Changing the periods, endpoint shape, or filename.

## Data Mapping

The three Pattern Analysis columns aggregate, over the incidents in the window:

| Column | Source | Example cell |
|--------|--------|--------------|
| Triggers | `incident.trigger` | `Sensory (5)` |
| Behaviors | `incident.type` | `Behavioural (4)` |
| Actions Taken | `incident.interventions` (m2m → each `.name`) | `Calm Space (6)` |

Each column is an independent ranked count distribution (most frequent first, ties broken
alphabetically). Columns of unequal length are padded with blank cells for row alignment.

## Architecture

Two units, both already existing; this is a focused refactor.

### `reports.py`

**New helper:**
```python
def _count_dist(values):
    """[(label, count)] sorted by count desc then label asc; skips empty values."""
```

**`build_child_report(child, incidents, period, today)`** — add these keys to the returned
dict (all existing keys stay unchanged, so the v1 endpoint keeps working):
- `age`: `child.age` if not None else `"—"`.
- `school_roll`: `""` (filled by the endpoint, like `school`).
- `trigger_counts`: `_count_dist([i.trigger for i in incidents])`.
- `behavior_counts`: `_count_dist([i.type for i in incidents])`.
- `action_counts`: `_count_dist([iv.name for i in incidents for iv in i.interventions])`.

`pattern_text` is retained as a one-line narrative intro shown above the 3-column table.

**`render_child_report_pdf(report)`** — rewrite the layout (Helvetica throughout, visible grid
lines). Keep all ReportLab imports lazy (inside the function) so `reports.py` stays importable
without ReportLab for the pure tests. Sections, in order:
1. **Header band:** title "EDI AI Behaviour Report"; sub-line
   `"{school} · Roll Number: {school_roll} · Generated {generated_on}"` (the Roll Number clause
   is omitted if `school_roll` is empty).
2. **Student Details** (bordered table, bold labels): `Student`, `Class`, `Key Worker`, `Age`,
   and a `Period` row (`{period_label} ({period_range})`).
3. **Key Stats** row (unchanged): Total Incidents, Per Week Avg, Top Severity, Avg Duration.
4. **Incident Summary** (unchanged per-incident table): Date, Type, Severity, Trigger, Outcome;
   or the "No incidents recorded in this period." line when empty.
5. **Pattern Analysis:** the `pattern_text` intro line, then a 3-column table
   (`Triggers | Behaviors | Actions Taken`) of `"{label} ({count})"` cells, padded for
   alignment. When there are no incidents, show only the empty-state line (no table).
6. **Footer on every page** (drawn by a local `NumberedCanvas(canvas.Canvas)` subclass passed
   via `doc.build(story, canvasmaker=...)`): left = `"{child_name} · Generated {generated_on}"`,
   right = `"Page {x} of {y}"`, plus `"CONFIDENTIAL"`. Helvetica 8pt, grey.

`NumberedCanvas` collects page states in `showPage()` and, in `save()`, replays them to draw
the footer with the known total page count (`y`).

### `reports_api.py`

In `child_report`, replace the single school-name fill with both fields:
```python
sc = serialize_system_config(SystemConfig.query.first())
report["school"] = sc["name"]
report["school_roll"] = sc["roll_number"]
```
Everything else (period validation, incident query, filename, Response) is unchanged.

## Testing

**`tests/test_reports.py` (modify):**

- `test_count_dist_orders_by_count_then_label` (new) — `_count_dist(["B","A","A","B","C","B"])`
  == `[("B",3),("A",2),("C",1)]`; `_count_dist([])` == `[]`; `_count_dist([None,"","X"])` ==
  `[("X",1)]`.
- `test_build_child_report_aggregates` (update) — give the `child` an `age` and give incidents
  `interventions` lists (of `SimpleNamespace(name=...)`); assert `age`, `trigger_counts`,
  `behavior_counts`, `action_counts` alongside the existing assertions.
- `test_build_child_report_empty` (update) — `child.age=None` → `age == "—"`;
  `trigger_counts == behavior_counts == action_counts == []`.
- `test_render_child_report_pdf_returns_pdf_bytes` (update) — extend the input dict with the
  new keys (`age`, `school_roll`, `trigger_counts`, `behavior_counts`, `action_counts`);
  still asserts `out[:4] == b"%PDF"`.
- `test_render_child_report_pdf_empty_state` (update) — same new keys with empty lists; renders.
- Endpoint tests (`test_child_report_*`) are unchanged and must stay green.

Page-numbering and visual layout are confirmed by the render smoke tests (valid `%PDF`) plus a
manual browser regeneration — PDF text content is not byte-asserted.

## Manual Verification (regeneration)

After implementation: run `python app.py`, log a couple of incidents (with interventions) for a
child via Log Incident, then Reports → Individual Child → Generate. Open the PDF and confirm:
the header shows School Name + Roll Number; Student Details lists student/class/key worker/age;
Pattern Analysis shows real counts in three columns; every page footer shows "Page X of Y" with
the student name and date.

## Done Criteria

- `python -m pytest -q` green (existing suite + updated/new report tests).
- The generated PDF shows: dynamic School Name + Roll Number; a bordered Student Details table;
  a 3-column aggregated Pattern Analysis with real counts; per-incident Incident Summary;
  a "Page X of Y" footer with student name + date on every page; Helvetica throughout with
  clear table grid lines.
- Empty-window reports still render a valid PDF.
- The endpoint, periods, and filename are unchanged from v1.
