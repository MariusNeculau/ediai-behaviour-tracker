# Plan: Seizure Log v2

**Depends on:** Seizure log v1 (implemented in therapy sessions commit `9803a9b`)  
**Goal:** Surface seizure data meaningfully — dedicated views, child-level statistics, edit capability, PDF integration, and a printable emergency card.

---

## Current State (v1)

- `SeizureDetail` model — satellite table 1:0..1 with `Incident` (unique FK)
- `Incident.subtype` field — `"Epileptic Seizure"` triggers the detail form
- `POST /api/incidents` accepts nested `seizureDetail` payload
- Log Incident form — seizure section appears when type=Crisis + subtype=Epileptic Seizure
- Incident modal — shows seizure details if present
- **Not yet:** dedicated list view, stats, edit, PDF section, export, emergency card

---

## Scope

Six deliverables, ordered by value-to-effort ratio:

| # | Deliverable | Effort | Value |
|---|---|---|---|
| 1 | Edit seizure details after save | S | High |
| 2 | Seizure stats in Child Profile | S | High |
| 3 | Seizure log view (school-wide list) | M | High |
| 4 | Seizure section in Individual Child PDF | M | High |
| 5 | Emergency Protocol Card (printable) | M | High |
| 6 | Seizure CSV export | S | Medium |

---

## Deliverable 1 — Edit Seizure Details After Save

**Problem:** Currently a `SeizureDetail` is created at incident POST time. There is no way to correct or complete it afterwards.

### Backend

Add `PUT /api/incidents/<id>/seizure` in `sessions_api.py` (or a new `seizure_api.py`):

```python
@sessions_bp.route("/incidents/<int:incident_id>/seizure", methods=["PUT"])
def update_seizure_detail(incident_id):
    incident = db.session.get(Incident, incident_id)
    if incident is None:
        return jsonify({"error": "Unknown incident"}), 404

    data = request.get_json(silent=True) or {}
    sd = incident.seizure_detail

    if sd is None:
        # Create if missing (incident pre-dated v1 or was logged without detail)
        if incident.subtype != "Epileptic Seizure":
            incident.subtype = "Epileptic Seizure"
        sd = SeizureDetail(incident_id=incident_id)
        db.session.add(sd)

    for field, col in [
        ("seizureType",            "seizure_type"),
        ("durationSeconds",        "duration_seconds"),
        ("recoveryTimeMinutes",    "recovery_time_minutes"),
        ("positionDuring",         "position_during"),
        ("emergencyServicesCalled","emergency_services_called"),
        ("protocolFollowed",       "protocol_followed"),
        ("medicationAdministered", "medication_administered"),
        ("medicationName",         "medication_name"),
        ("postIctalNotes",         "post_ictal_notes"),
    ]:
        if field in data:
            setattr(sd, col, data[field])

    db.session.commit()
    return jsonify(serialize_seizure_detail(sd))
```

### Frontend

In `showIncidentModal()`, add an **Edit Seizure Details** button when `i.subtype === 'Epileptic Seizure'`. Opens a modal pre-filled with existing `i.seizureDetail` values. On save, calls `PUT /api/incidents/<id>/seizure` and updates `INCIDENTS` in place.

**Files:** `sessions_api.py`, `serializers.py`, `templates/dashboard.html`  
**Tests:** `test_update_seizure_detail_existing()`, `test_update_seizure_detail_creates_if_missing()`, `test_update_seizure_detail_unknown_incident_returns_404()`

---

## Deliverable 2 — Seizure Stats in Child Profile

**What:** Add a "Seizure History" mini-stats card to `renderChildDetail()`, loaded alongside the therapy summary. Only shown if the child has at least one seizure incident.

### Backend

Add `GET /api/children/<id>/seizure-summary`:

```python
@settings_bp.route("/children/<int:child_id>/seizure-summary", methods=["GET"])
def child_seizure_summary(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404

    seizure_incidents = (
        Incident.query
        .filter_by(child_id=child_id, subtype="Epileptic Seizure")
        .order_by(Incident.occurred_at.desc())
        .all()
    )
    if not seizure_incidents:
        return jsonify({"count": 0, "incidents": []})

    details = [i.seizure_detail for i in seizure_incidents if i.seizure_detail]
    durations = [d.duration_seconds for d in details if d.duration_seconds]
    avg_duration = round(sum(durations) / len(durations)) if durations else None
    protocol_rate = (
        round(sum(1 for d in details if d.protocol_followed) / len(details) * 100)
        if details else None
    )
    type_counts = Counter(d.seizure_type for d in details if d.seizure_type)
    most_common_type = type_counts.most_common(1)[0][0] if type_counts else None

    return jsonify({
        "count": len(seizure_incidents),
        "lastDate": seizure_incidents[0].occurred_at.strftime("%d %b %Y"),
        "avgDurationSeconds": avg_duration,
        "protocolComplianceRate": protocol_rate,
        "mostCommonType": most_common_type,
        "incidents": [_serialize_seizure_incident(i) for i in seizure_incidents[:5]],
    })
```

### Frontend

In `showChildDetail()`, call `loadChildSeizureSummary(id)` alongside `loadChildTherapySummary(id)`. Render a card with:

```
Seizure History
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
12 total  ·  Last: 20 Jun 2026  ·  Most common: Tonic-Clonic
Avg duration: 95 sec  ·  Protocol compliance: 83%

[table: Date | Type | Duration | Position | Emergency | Protocol | Medication]
```

**Files:** `settings_api.py`, `templates/dashboard.html`  
**Tests:** `test_seizure_summary_empty_for_new_child()`, `test_seizure_summary_stats_correct()`, `test_seizure_summary_protocol_compliance_rate()`

---

## Deliverable 3 — Seizure Log View (School-wide List)

**What:** A dedicated "Seizure Log" section accessible from the Dashboard sidebar or from the Profiles tab — a filterable table of all epileptic seizure incidents across all children.

### Backend

Add `GET /api/seizures` — returns all incidents with `subtype="Epileptic Seizure"`, joined with their `SeizureDetail`:

```python
@sessions_bp.route("/seizures", methods=["GET"])
def list_seizures():
    child_id = request.args.get("childId", type=int)
    q = Incident.query.filter_by(subtype="Epileptic Seizure")
    if child_id:
        q = q.filter_by(child_id=child_id)
    incidents = q.order_by(Incident.occurred_at.desc()).all()
    return jsonify([_serialize_seizure_incident(i) for i in incidents])
```

### Frontend

New nav item **Seizure Log** in sidebar. Renders a filterable table:

| Date & Time | Child | Class | Seizure Type | Duration | Protocol | Emergency | Staff |
|---|---|---|---|---|---|---|---|

- Filter by child (dropdown)
- Click row → incident modal (existing, already shows seizure details)
- Red highlight on rows where `emergencyServicesCalled = true`
- Orange highlight on rows where `protocolFollowed = false`

**Files:** `sessions_api.py`, `templates/dashboard.html`  
**Tests:** `test_list_seizures_returns_only_epileptic_incidents()`, `test_list_seizures_filter_by_child()`

---

## Deliverable 4 — Seizure Section in Individual Child PDF

**What:** Add a "Seizure History" section to the Individual Child PDF report when the child has seizure incidents in the period.

### Backend change — `reports.py`

Extend `build_child_report()` with a `seizure_incidents=None` parameter (parallel to `goals`):

```python
def build_child_report(child, incidents, period, today, goals=None, seizure_incidents=None):
    ...existing...

    seizures = []
    if seizure_incidents:
        for i in seizure_incidents:
            sd = i.seizure_detail
            seizures.append({
                "date": i.occurred_at.strftime("%d %b %Y %H:%M"),
                "seizure_type": sd.seizure_type if sd else "—",
                "duration_seconds": sd.duration_seconds if sd else None,
                "position": sd.position_during if sd else "—",
                "protocol_followed": sd.protocol_followed if sd else False,
                "emergency_called": sd.emergency_services_called if sd else False,
                "medication": sd.medication_name if (sd and sd.medication_administered) else "—",
                "notes": sd.post_ictal_notes if sd else "—",
            })

    return {
        ...existing...,
        "seizures": seizures,
    }
```

In `render_report_pdf()`, add section after Therapy Progress:

```
Seizure History
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Date & Time | Type | Duration | Protocol | Emergency | Medication
```

In `reports_api.py` `child_report()`, query and pass seizure incidents:

```python
seizure_incidents = (
    Incident.query
    .filter(Incident.child_id == child_id,
            Incident.subtype == "Epileptic Seizure",
            Incident.occurred_at >= start_dt,
            Incident.occurred_at < end_dt)
    .order_by(Incident.occurred_at.desc())
    .all()
)
report = build_child_report(child, incidents, period, today,
                             goals=goals, seizure_incidents=seizure_incidents)
```

**Files:** `reports.py`, `reports_api.py`  
**Tests:** `test_build_child_report_includes_seizure_data()`, `test_child_report_pdf_with_seizures_valid()`

---

## Deliverable 5 — Emergency Protocol Card (Printable)

**What:** A single-page printable card per child containing:
- Child name, class, key worker, emergency contacts
- Seizure history summary (count, most common type, avg duration)
- Protocol steps (from school config)
- Last 3 seizures with key details

Accessible via a **Print Emergency Card** button in the Child Profile header.

### Backend

Add `GET /api/reports/child/<id>/emergency-card` — generates a compact 1-page PDF:

```python
@reports_bp.route("/reports/child/<int:child_id>/emergency-card", methods=["GET"])
def child_emergency_card(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404

    seizure_incidents = (
        Incident.query
        .filter_by(child_id=child_id, subtype="Epileptic Seizure")
        .order_by(Incident.occurred_at.desc())
        .limit(3).all()
    )
    pdf = render_emergency_card_pdf(child, seizure_incidents)
    # send as inline (not attachment) so browser can print
    ...
```

### Frontend

In `renderChildDetail()`, add button next to "Generate Report":

```html
<button class="btn-outline" onclick="printEmergencyCard(childId)">
  🖨 Emergency Card
</button>
```

`printEmergencyCard(id)` opens `GET /api/reports/child/<id>/emergency-card` in a new tab.

**Files:** `reports_api.py`, `reports.py` (new `render_emergency_card_pdf()`), `templates/dashboard.html`  
**Tests:** `test_emergency_card_returns_pdf()`, `test_emergency_card_unknown_child_returns_404()`

---

## Deliverable 6 — Seizure CSV Export

**What:** Export all seizure incidents with full `SeizureDetail` fields to CSV. Available from the Reports tab alongside the existing Incidents CSV export.

### Backend

Add `_seizure_to_csv_row()` and `seizures_to_csv()` in `exports.py`:

```python
_SEIZURE_HEADERS = [
    "Date", "Time", "Child", "Class", "Staff",
    "Seizure Type", "Duration (sec)", "Recovery (min)", "Position",
    "Emergency Services", "Protocol Followed",
    "Medication Administered", "Medication Name",
    "Post-ictal Notes", "Incident Notes",
]

def seizures_to_csv(incidents):
    rows = [_SEIZURE_HEADERS]
    for i in incidents:
        sd = i.seizure_detail
        dt = i.occurred_at
        rows.append([
            dt.strftime("%Y-%m-%d") if dt else "",
            dt.strftime("%H:%M") if dt else "",
            i.child.name if i.child else "",
            i.child.room.name if (i.child and i.child.room) else "",
            i.staff.name if i.staff else "",
            sd.seizure_type or "" if sd else "",
            str(sd.duration_seconds or "") if sd else "",
            str(sd.recovery_time_minutes or "") if sd else "",
            sd.position_during or "" if sd else "",
            "Yes" if (sd and sd.emergency_services_called) else "No",
            "Yes" if (sd and sd.protocol_followed) else "No",
            "Yes" if (sd and sd.medication_administered) else "No",
            sd.medication_name or "" if sd else "",
            sd.post_ictal_notes or "" if sd else "",
            i.notes or "",
        ])
    writer_output = io.StringIO()
    csv.writer(writer_output).writerows(rows)
    return writer_output.getvalue()
```

Add `GET /api/export/seizures.csv` in `reports_api.py` — mirrors `export_incidents_csv()`.

### Frontend

In `renderReports()`, add a second export button:

```html
<button class="btn-outline" onclick="exportSeizuresCsv()">
  ↧ Export Seizure Log (CSV)
</button>
```

**Files:** `exports.py`, `reports_api.py`, `templates/dashboard.html`  
**Tests:** `test_seizures_to_csv_header()`, `test_seizures_to_csv_row_with_detail()`, `test_seizures_to_csv_row_without_detail()`, `test_export_seizures_csv_endpoint()`

---

## Delivery Sequence

```
Week 1:  D1 (edit seizure) + D6 (CSV export) — isolated, no dependencies
Week 2:  D2 (child profile stats) + D3 (seizure log view)
Week 3:  D4 (PDF section)
Week 4:  D5 (emergency card) — most complex, depends on D2 stats logic
```

Each deliverable ships independently with its own tests.

---

## Test File

New tests go in `tests/test_seizures.py`. Suggested base fixture:

```python
@pytest.fixture
def seizure_incident_id(app, client, child_id):
    from models import db, Incident, SeizureDetail, Staff
    from datetime import datetime

    with app.app_context():
        staff = Staff.query.first()
        inc = Incident(
            child_id=child_id,
            staff_id=staff.id if staff else None,
            occurred_at=datetime(2026, 6, 20, 10, 15),
            type="Crisis",
            subtype="Epileptic Seizure",
            severity="High",
            description="Tonic-clonic episode in classroom",
            status="Resolved",
        )
        db.session.add(inc)
        db.session.flush()
        sd = SeizureDetail(
            incident_id=inc.id,
            seizure_type="Tonic-Clonic",
            duration_seconds=90,
            recovery_time_minutes=15,
            position_during="Floor",
            emergency_services_called=False,
            protocol_followed=True,
            medication_administered=False,
        )
        db.session.add(sd)
        db.session.commit()
        return inc.id
```
