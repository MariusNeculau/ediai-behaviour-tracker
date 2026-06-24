"""reports_api.py — endpoint-uri de generare rapoarte (PDF).

Înregistrat sub /api de app.create_app(). v1: raport pentru un copil individual,
generat la cerere și trimis ca download (fără stocare pe disc).
"""

import re
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request

from models import db, Child, Incident, Room, SystemConfig, TherapyGoal
from serializers import serialize_system_config
from flask import Response
from reports import (
    period_start, build_child_report, build_class_report, build_school_report,
    render_report_pdf, render_emergency_card_pdf,
)
from exports import incidents_to_csv, seizures_to_csv
from report_storage import save_report, list_saved_reports, FOLDER_NAME

reports_bp = Blueprint("reports", __name__, url_prefix="/api")


@reports_bp.route("/reports/child/<int:child_id>/emergency-card", methods=["GET"])
def child_emergency_card(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404

    seizure_incidents = (
        Incident.query
        .filter_by(child_id=child_id, subtype="Epileptic Seizure")
        .order_by(Incident.occurred_at.desc())
        .limit(3)
        .all()
    )
    sc = serialize_system_config(SystemConfig.query.first())
    pdf = render_emergency_card_pdf(
        child, seizure_incidents, sc["name"], sc["roll_number"]
    )
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", child.name).strip("_") or "child"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=EDI_AI_EmergencyCard_{safe_name}.pdf"},
    )


@reports_bp.route("/reports/saved", methods=["GET"])
def list_reports():
    return jsonify({"reports": list_saved_reports()})


def _window_bounds(period, today):
    """(start_dt, end_dt) pentru fereastra rolling; ridică ValueError la period invalid."""
    start = period_start(period, today)
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())
    return start_dt, end_dt


@reports_bp.route("/reports/child/<int:child_id>", methods=["GET"])
def child_report(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404

    period = request.args.get("period", "month")
    today = date.today()
    try:
        start_dt, end_dt = _window_bounds(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    incidents = (
        Incident.query
        .filter(Incident.child_id == child_id,
                Incident.occurred_at >= start_dt,
                Incident.occurred_at < end_dt)
        .order_by(Incident.occurred_at.desc())
        .all()
    )

    goals = TherapyGoal.query.filter_by(child_id=child_id).all()
    seizure_incidents = (
        Incident.query
        .filter(
            Incident.child_id == child_id,
            Incident.subtype == "Epileptic Seizure",
            Incident.occurred_at >= start_dt,
            Incident.occurred_at < end_dt,
        )
        .order_by(Incident.occurred_at.desc())
        .all()
    )
    report = build_child_report(child, incidents, period, today,
                                 goals=goals, seizure_incidents=seizure_incidents)
    sc = serialize_system_config(SystemConfig.query.first())
    report["school"] = sc["name"]
    report["school_roll"] = sc["roll_number"]
    pdf = render_report_pdf(report)

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", child.name).strip("_") or "child"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_Report_{safe_name}_{period}_{stamp}.pdf"
    try:
        save_report(filename, pdf)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})


@reports_bp.route("/reports/class/<int:room_id>", methods=["GET"])
def class_report(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Unknown class"}), 404

    period = request.args.get("period", "month")
    today = date.today()
    try:
        start_dt, end_dt = _window_bounds(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    children = Child.query.filter_by(room_id=room_id, active=True).all()
    child_ids = [c.id for c in children]
    incidents = (
        Incident.query
        .filter(Incident.child_id.in_(child_ids),
                Incident.occurred_at >= start_dt,
                Incident.occurred_at < end_dt)
        .all()
    ) if child_ids else []

    report = build_class_report(room, children, incidents, period, today)
    sc = serialize_system_config(SystemConfig.query.first())
    report["school"] = sc["name"]
    report["school_roll"] = sc["roll_number"]
    pdf = render_report_pdf(report)

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", room.name).strip("_") or "class"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_Report_Class_{safe_name}_{period}_{stamp}.pdf"
    try:
        save_report(filename, pdf)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})


@reports_bp.route("/reports/school", methods=["GET"])
def school_report():
    period = request.args.get("period", "month")
    today = date.today()
    try:
        start_dt, end_dt = _window_bounds(period, today)
    except ValueError:
        return jsonify({"error": "Invalid period"}), 400

    rooms = Room.query.filter_by(active=True).order_by(Room.name).all()
    children = Child.query.filter_by(active=True).all()
    child_ids = [c.id for c in children]
    incidents = (
        Incident.query
        .filter(Incident.child_id.in_(child_ids),
                Incident.occurred_at >= start_dt,
                Incident.occurred_at < end_dt)
        .all()
    ) if child_ids else []

    report = build_school_report(rooms, children, incidents, period, today)
    sc = serialize_system_config(SystemConfig.query.first())
    report["school"] = sc["name"]
    report["school_roll"] = sc["roll_number"]
    pdf = render_report_pdf(report)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_Report_Whole_School_{period}_{stamp}.pdf"
    try:
        save_report(filename, pdf)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})


@reports_bp.route("/export/seizures.csv", methods=["GET"])
def export_seizures_csv():
    incidents = (
        Incident.query
        .filter_by(subtype="Epileptic Seizure")
        .order_by(Incident.occurred_at.desc())
        .all()
    )
    data = ("﻿" + seizures_to_csv(incidents)).encode("utf-8")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_SeizureLog_{stamp}.csv"
    try:
        save_report(filename, data)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})


@reports_bp.route("/export/incidents.csv", methods=["GET"])
def export_incidents_csv():
    incidents = Incident.query.order_by(Incident.occurred_at.desc()).all()
    data = ("﻿" + incidents_to_csv(incidents)).encode("utf-8")   # BOM so Excel detects UTF-8
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_Incidents_{stamp}.csv"
    try:
        save_report(filename, data)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})
