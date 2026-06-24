"""sessions_api.py — CRUD blueprint for TherapyGoal and TherapySession.

Endpoints:
    GET  /api/goals                        list goals (filter: ?childId=)
    POST /api/goals                        create goal (supervisor)
    PUT  /api/goals/<id>                   update goal
    GET  /api/goals/<id>/sessions          list sessions for a goal

    GET  /api/therapy-sessions             list all sessions (filter: ?childId=, ?goalId=)
    POST /api/therapy-sessions             create planned session
    PUT  /api/therapy-sessions/<id>        update / complete session
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

import config
from models import db, Child, Staff, TherapyGoal, TherapySession, Incident, SeizureDetail
from serializers import (
    serialize_goal, serialize_therapy_session,
    serialize_seizure_detail, serialize_seizure_incident,
)

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api")


# ─── Seizure Log ─────────────────────────────────────────────────────────────

@sessions_bp.route("/seizures", methods=["GET"])
def list_seizures():
    child_id = request.args.get("childId", type=int)
    q = Incident.query.filter_by(subtype="Epileptic Seizure")
    if child_id:
        q = q.filter_by(child_id=child_id)
    incidents = q.order_by(Incident.occurred_at.desc()).all()
    return jsonify([serialize_seizure_incident(i) for i in incidents])


# ─── Seizure Detail ──────────────────────────────────────────────────────────

@sessions_bp.route("/incidents/<int:incident_id>/seizure", methods=["PUT"])
def update_seizure_detail(incident_id):
    incident = db.session.get(Incident, incident_id)
    if incident is None:
        return jsonify({"error": "Unknown incident"}), 404

    data = request.get_json(silent=True) or {}

    if "seizureType" in data and data["seizureType"] and \
            data["seizureType"] not in config.SEIZURE_TYPES:
        return jsonify({"error": "Invalid seizure type"}), 400
    if "positionDuring" in data and data["positionDuring"] and \
            data["positionDuring"] not in config.SEIZURE_POSITIONS:
        return jsonify({"error": "Invalid position"}), 400

    sd = incident.seizure_detail
    if sd is None:
        incident.subtype = "Epileptic Seizure"
        sd = SeizureDetail(incident_id=incident_id)
        db.session.add(sd)

    field_map = [
        ("seizureType",             "seizure_type"),
        ("durationSeconds",         "duration_seconds"),
        ("recoveryTimeMinutes",     "recovery_time_minutes"),
        ("positionDuring",          "position_during"),
        ("emergencyServicesCalled", "emergency_services_called"),
        ("protocolFollowed",        "protocol_followed"),
        ("medicationAdministered",  "medication_administered"),
        ("medicationName",          "medication_name"),
        ("postIctalNotes",          "post_ictal_notes"),
    ]
    for json_key, col in field_map:
        if json_key in data:
            value = data[json_key]
            # Store empty strings as NULL — consistent with how other text fields behave
            if value == "":
                value = None
            setattr(sd, col, value)

    db.session.commit()
    return jsonify(serialize_seizure_detail(sd))


# ─── Goals ──────────────────────────────────────────────────────────────────

@sessions_bp.route("/goals", methods=["GET"])
def list_goals():
    q = TherapyGoal.query
    child_id = request.args.get("childId", type=int)
    if child_id:
        q = q.filter_by(child_id=child_id)
    goals = q.order_by(TherapyGoal.created_at.desc()).all()
    return jsonify([serialize_goal(g) for g in goals])


@sessions_bp.route("/goals", methods=["POST"])
def create_goal():
    data = request.get_json(silent=True) or {}

    child_id = data.get("childId")
    child = db.session.get(Child, child_id) if child_id else None
    if child is None or not child.active:
        return jsonify({"error": "A valid active child is required"}), 400

    skill_area = (data.get("skillArea") or "").strip()
    if skill_area not in config.THERAPY_SKILL_AREAS:
        return jsonify({"error": "Invalid skill area"}), 400

    description = (data.get("description") or "").strip()
    if not description:
        return jsonify({"error": "Description is required"}), 400

    created_by_id = data.get("createdById") or None
    if created_by_id:
        staff = db.session.get(Staff, created_by_id)
        if staff is None or not staff.active:
            return jsonify({"error": "Unknown staff member"}), 400

    goal = TherapyGoal(
        child_id=child.id,
        created_by_id=created_by_id,
        skill_area=skill_area,
        description=description,
        target_criteria=(data.get("targetCriteria") or "").strip() or None,
        status="Active",
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify(serialize_goal(goal)), 201


@sessions_bp.route("/goals/<int:goal_id>", methods=["PUT"])
def update_goal(goal_id):
    goal = db.session.get(TherapyGoal, goal_id)
    if goal is None:
        return jsonify({"error": "Unknown goal"}), 404

    data = request.get_json(silent=True) or {}

    if "skillArea" in data:
        skill_area = (data["skillArea"] or "").strip()
        if skill_area not in config.THERAPY_SKILL_AREAS:
            return jsonify({"error": "Invalid skill area"}), 400
        goal.skill_area = skill_area

    if "description" in data:
        desc = (data["description"] or "").strip()
        if not desc:
            return jsonify({"error": "Description is required"}), 400
        goal.description = desc

    if "targetCriteria" in data:
        goal.target_criteria = (data["targetCriteria"] or "").strip() or None

    if "status" in data:
        status = data["status"]
        if status not in config.GOAL_STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        goal.status = status
        if status == "Achieved" and goal.achieved_at is None:
            goal.achieved_at = datetime.utcnow()

    db.session.commit()
    return jsonify(serialize_goal(goal))


@sessions_bp.route("/goals/<int:goal_id>/sessions", methods=["GET"])
def list_sessions_for_goal(goal_id):
    goal = db.session.get(TherapyGoal, goal_id)
    if goal is None:
        return jsonify({"error": "Unknown goal"}), 404
    sessions = (
        TherapySession.query
        .filter_by(goal_id=goal_id)
        .order_by(TherapySession.planned_at.desc())
        .all()
    )
    return jsonify([serialize_therapy_session(s) for s in sessions])


# ─── Therapy Sessions ────────────────────────────────────────────────────────

@sessions_bp.route("/therapy-sessions", methods=["GET"])
def list_therapy_sessions():
    q = TherapySession.query
    child_id = request.args.get("childId", type=int)
    goal_id = request.args.get("goalId", type=int)
    if child_id:
        q = q.filter_by(child_id=child_id)
    if goal_id:
        q = q.filter_by(goal_id=goal_id)
    sessions = q.order_by(TherapySession.planned_at.desc()).all()
    return jsonify([serialize_therapy_session(s) for s in sessions])


@sessions_bp.route("/therapy-sessions", methods=["POST"])
def create_therapy_session():
    data = request.get_json(silent=True) or {}

    child_id = data.get("childId")
    child = db.session.get(Child, child_id) if child_id else None
    if child is None or not child.active:
        return jsonify({"error": "A valid active child is required"}), 400

    goal_id = data.get("goalId")
    goal = db.session.get(TherapyGoal, goal_id) if goal_id else None
    if goal is None:
        return jsonify({"error": "A valid goal is required"}), 400
    if goal.child_id != child.id:
        return jsonify({"error": "Goal does not belong to this child"}), 400

    planned_by_id = data.get("plannedById") or None
    if planned_by_id and db.session.get(Staff, planned_by_id) is None:
        return jsonify({"error": "Unknown staff member (plannedBy)"}), 400

    planned_at = None
    if data.get("plannedAt"):
        try:
            planned_at = datetime.fromisoformat(data["plannedAt"])
        except ValueError:
            return jsonify({"error": "Invalid plannedAt format (ISO 8601 expected)"}), 400

    session = TherapySession(
        child_id=child.id,
        goal_id=goal.id,
        planned_by_id=planned_by_id,
        planned_at=planned_at,
        status="Planned",
    )
    db.session.add(session)
    db.session.commit()
    return jsonify(serialize_therapy_session(session)), 201


@sessions_bp.route("/therapy-sessions/<int:session_id>", methods=["PUT"])
def update_therapy_session(session_id):
    session = db.session.get(TherapySession, session_id)
    if session is None:
        return jsonify({"error": "Unknown therapy session"}), 404

    data = request.get_json(silent=True) or {}

    if "status" in data:
        status = data["status"]
        if status not in config.SESSION_STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        session.status = status

    if "conductedById" in data:
        conducted_by_id = data["conductedById"] or None
        if conducted_by_id and db.session.get(Staff, conducted_by_id) is None:
            return jsonify({"error": "Unknown staff member (conductedBy)"}), 400
        session.conducted_by_id = conducted_by_id

    if "conductedAt" in data:
        try:
            session.conducted_at = (
                datetime.fromisoformat(data["conductedAt"]) if data["conductedAt"] else None
            )
        except ValueError:
            return jsonify({"error": "Invalid conductedAt format (ISO 8601 expected)"}), 400

    if "totalTrials" in data:
        session.total_trials = data["totalTrials"]

    if "correctTrials" in data:
        session.correct_trials = data["correctTrials"]

    if "promptLevel" in data:
        prompt_level = data["promptLevel"]
        if prompt_level and prompt_level not in config.PROMPT_LEVELS:
            return jsonify({"error": "Invalid prompt level"}), 400
        session.prompt_level = prompt_level or None

    if "notes" in data:
        session.notes = (data["notes"] or "").strip() or None

    db.session.commit()
    return jsonify(serialize_therapy_session(session))
