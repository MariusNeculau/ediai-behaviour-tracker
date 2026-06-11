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
