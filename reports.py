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


def _count_dist(values):
    """[(label, count)] sortat după count desc apoi label asc; ignoră valorile goale."""
    items = [v for v in values if v]
    if not items:
        return []
    counts = Counter(items)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


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

    footer_left = "Confidential - EDI AI Report"

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
    sub = ParagraphStyle("rsub", parent=styles["Normal"], fontName="Helvetica",
                         fontSize=9, textColor=colors.grey, alignment=1)
    h2 = ParagraphStyle("rh2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                        fontSize=12, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("rbody", parent=styles["Normal"], fontName="Helvetica", fontSize=10)

    grey_grid = colors.HexColor("#bdbdbd")
    head_bg = colors.HexColor("#e8eef7")
    box_border = colors.HexColor("#7a7a7a")

    story = []

    # 1. Header band (centered, bold school identity)
    story.append(Paragraph("EDI AI Behaviour Report", h1))
    roll = report.get("school_roll") or ""
    school_line = report["school"]
    if roll:
        school_line += f" · Roll Number: {roll}"
    story.append(Paragraph(school_line, school_style))
    story.append(Paragraph(f"Generated {report['generated_on']}", sub))
    story.append(Spacer(1, 12))

    # 2. Student Details
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
    story.append(Spacer(1, 12))

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
        ("INNERGRID", (0, 0), (-1, -1), 0.5, grey_grid),
        ("BOX", (0, 0), (-1, -1), 1.0, box_border),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stats_tbl)
    story.append(Spacer(1, 12))

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
    story.append(Spacer(1, 12))

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
