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
