"""reports.py — construirea rapoartelor de comportament (date + PDF).

Agregarea (period_start, build_child_report) este pură: primește modele deja
încărcate și liste, nu atinge sesiunea DB sau Flask — ușor de testat.
Randarea PDF (render_child_report_pdf) folosește ReportLab Platypus.
"""

from collections import Counter
from datetime import datetime, timedelta
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


def build_child_report(child, incidents, period, today, goals=None):
    """View-model pur (dict) pentru raportul unui copil. `school` e completat de endpoint.

    `goals` — listă opțională de TherapyGoal pentru copil; când e furnizată,
    raportul include o secțiune Therapy Progress cu sesiunile din fereastră.
    """
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

    therapy = []
    if goals:
        start_dt = datetime.combine(start, datetime.min.time())
        for g in goals:
            completed = [
                s for s in g.sessions
                if s.status == "Completed"
                and s.conducted_at is not None
                and s.conducted_at >= start_dt
            ]
            if not completed:
                continue
            accuracies = [
                round(s.correct_trials / s.total_trials * 100)
                for s in completed
                if s.total_trials and s.correct_trials is not None
            ]
            therapy.append({
                "skill_area": g.skill_area,
                "description": g.description,
                "target_criteria": g.target_criteria or "—",
                "status": g.status,
                "sessions_count": len(completed),
                "avg_accuracy": round(sum(accuracies) / len(accuracies)) if accuracies else None,
            })

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
        "therapy": therapy,
        **agg,
    }


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

    # 6. Therapy Progress (child report only, when therapy data is present)
    therapy = report.get("therapy") or []
    if rtype == "child" and therapy:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Therapy Progress", h2))
        th_data = [["Skill Area", "Sessions", "Avg Accuracy", "Status", "Target Criteria"]]
        for t in therapy:
            acc = f"{t['avg_accuracy']}%" if t["avg_accuracy"] is not None else "—"
            th_data.append([
                t["skill_area"],
                str(t["sessions_count"]),
                acc,
                t["status"],
                t["target_criteria"],
            ])
        th_tbl = Table(th_data, colWidths=[38 * mm, 22 * mm, 26 * mm, 22 * mm, 66 * mm],
                       repeatRows=1)
        th_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), head_bg),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (2, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, grey_grid),
            ("BOX", (0, 0), (-1, -1), 1.0, box_border),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(th_tbl)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


# Back-compat: vechiul nume folosit inainte de generalizare.
render_child_report_pdf = render_report_pdf
