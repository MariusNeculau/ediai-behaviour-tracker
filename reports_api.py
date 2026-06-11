"""reports_api.py — endpoint-uri de generare rapoarte (PDF).

Înregistrat sub /api de app.create_app(). v1: raport pentru un copil individual,
generat la cerere și trimis ca download (fără stocare pe disc).
"""

import re
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, jsonify, request

from models import db, Child, Incident, SystemConfig
from serializers import serialize_system_config
from reports import period_start, build_child_report, render_child_report_pdf

reports_bp = Blueprint("reports", __name__, url_prefix="/api")


@reports_bp.route("/reports/child/<int:child_id>", methods=["GET"])
def child_report(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404

    period = request.args.get("period", "month")
    today = date.today()
    try:
        start = period_start(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())
    incidents = (
        Incident.query
        .filter(Incident.child_id == child_id,
                Incident.occurred_at >= start_dt,
                Incident.occurred_at < end_dt)
        .order_by(Incident.occurred_at.desc())
        .all()
    )

    report = build_child_report(child, incidents, period, today)
    report["school"] = serialize_system_config(SystemConfig.query.first())["name"]
    pdf = render_child_report_pdf(report)

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", child.name).strip("_") or "child"
    filename = f"EDI_AI_Report_{safe_name}_{period}_{today:%Y%m%d}.pdf"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
