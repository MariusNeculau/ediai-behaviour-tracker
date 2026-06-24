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


SEIZURE_CSV_HEADER = [
    "Date", "Time", "Child", "Class", "Staff",
    "Seizure Type", "Duration (sec)", "Recovery (min)", "Position",
    "Emergency Services Called", "Protocol Followed",
    "Medication Administered", "Medication Name",
    "Post-ictal Notes", "Incident Notes",
]


def seizures_to_csv(incidents):
    """Întoarce un string CSV cu toate incidentele de tip Epileptic Seizure."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(SEIZURE_CSV_HEADER)
    for i in incidents:
        dt = i.occurred_at
        sd = i.seizure_detail
        writer.writerow([
            dt.strftime("%Y-%m-%d") if dt else "",
            dt.strftime("%H:%M") if dt else "",
            i.child.name if i.child else "",
            i.child.room.name if (i.child and i.child.room) else "",
            i.staff.name if i.staff else "",
            sd.seizure_type or "" if sd else "",
            sd.duration_seconds if (sd and sd.duration_seconds is not None) else "",
            sd.recovery_time_minutes if (sd and sd.recovery_time_minutes is not None) else "",
            sd.position_during or "" if sd else "",
            "Yes" if (sd and sd.emergency_services_called) else "No",
            "Yes" if (sd and sd.protocol_followed) else "No",
            "Yes" if (sd and sd.medication_administered) else "No",
            sd.medication_name or "" if sd else "",
            sd.post_ictal_notes or "" if sd else "",
            i.notes or "",
        ])
    return buf.getvalue()
