"""settings_api.py — CRUD blueprint for the managed entities.

Registered under /api by app.create_app(). Covers Rooms, Staff, and Children.
Deletion is soft (active=False). Archiving an entity that is still in use
(a Room with active children, or a Staff who is an active key worker) is
refused with HTTP 409 and an actionable message.
"""

from flask import Blueprint, jsonify, request

import config
from models import db, Child, Staff, Room, SystemConfig
from serializers import serialize_room, serialize_staff, serialize_child, serialize_system_config

settings_bp = Blueprint("settings", __name__, url_prefix="/api")


# ─── Rooms ──────────────────────────────────────────────────────────────────

@settings_bp.route("/rooms", methods=["GET"])
def list_rooms():
    q = Room.query if request.args.get("all") else Room.query.filter_by(active=True)
    return jsonify([serialize_room(r) for r in q.order_by(Room.name).all()])


@settings_bp.route("/rooms", methods=["POST"])
def create_room():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if Room.query.filter_by(name=name).first():
        return jsonify({"error": "A class with that name already exists"}), 400
    room = Room(name=name)
    db.session.add(room)
    db.session.commit()
    return jsonify(serialize_room(room)), 201


@settings_bp.route("/rooms/<int:room_id>", methods=["PUT"])
def update_room(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Unknown room"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if Room.query.filter(Room.name == name, Room.id != room_id).first():
        return jsonify({"error": "A class with that name already exists"}), 400
    room.name = name
    db.session.commit()
    return jsonify(serialize_room(room))


@settings_bp.route("/rooms/<int:room_id>", methods=["DELETE"])
def delete_room(room_id):
    room = db.session.get(Room, room_id)
    if room is None:
        return jsonify({"error": "Unknown room"}), 404
    in_use = Child.query.filter_by(room_id=room_id, active=True).count()
    if in_use:
        return jsonify({"error": f"Reassign {in_use} student(s) to another class first"}), 409
    room.active = False
    db.session.commit()
    return jsonify(serialize_room(room))


# ─── Staff ──────────────────────────────────────────────────────────────────

@settings_bp.route("/staff", methods=["GET"])
def list_staff():
    q = Staff.query if request.args.get("all") else Staff.query.filter_by(active=True)
    return jsonify([serialize_staff(s) for s in q.order_by(Staff.name).all()])


@settings_bp.route("/staff", methods=["POST"])
def create_staff():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if Staff.query.filter_by(name=name).first():
        return jsonify({"error": "A staff member with that name already exists"}), 400
    member = Staff(name=name, role=(data.get("role") or "").strip() or None)
    db.session.add(member)
    db.session.commit()
    return jsonify(serialize_staff(member)), 201


@settings_bp.route("/staff/<int:staff_id>", methods=["PUT"])
def update_staff(staff_id):
    member = db.session.get(Staff, staff_id)
    if member is None:
        return jsonify({"error": "Unknown staff member"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if Staff.query.filter(Staff.name == name, Staff.id != staff_id).first():
        return jsonify({"error": "A staff member with that name already exists"}), 400
    member.name = name
    member.role = (data.get("role") or "").strip() or None
    db.session.commit()
    return jsonify(serialize_staff(member))


@settings_bp.route("/staff/<int:staff_id>", methods=["DELETE"])
def delete_staff(staff_id):
    member = db.session.get(Staff, staff_id)
    if member is None:
        return jsonify({"error": "Unknown staff member"}), 404
    in_use = Child.query.filter_by(key_worker_id=staff_id, active=True).count()
    if in_use:
        return jsonify({"error": f"Reassign {in_use} student(s) to another key worker first"}), 409
    member.active = False
    db.session.commit()
    return jsonify(serialize_staff(member))


# ─── Children ───────────────────────────────────────────────────────────────

def _resolve_child_payload(data):
    """Validate a child payload. Returns (fields, error, status)."""
    name = (data.get("name") or "").strip()
    if not name:
        return None, "Name is required", 400

    room_id = data.get("roomId")
    room = db.session.get(Room, room_id) if room_id else None
    if room is None or not room.active:
        return None, "A valid class is required", 400

    key_worker_id = data.get("keyWorkerId") or None
    if key_worker_id:
        kw = db.session.get(Staff, key_worker_id)
        if kw is None or not kw.active:
            return None, "Unknown key worker", 400

    support = data.get("support")
    if support and support not in config.SUPPORT_LEVELS:
        return None, "Invalid support level", 400

    fields = {
        "name": name,
        "room_id": room.id,
        "key_worker_id": key_worker_id,
        "age": data.get("age"),
        "support": support,
    }
    return fields, None, None


@settings_bp.route("/children", methods=["GET"])
def list_children():
    q = Child.query if request.args.get("all") else Child.query.filter_by(active=True)
    return jsonify([serialize_child(c) for c in q.order_by(Child.name).all()])


@settings_bp.route("/children", methods=["POST"])
def create_child():
    data = request.get_json(silent=True) or {}
    fields, error, status = _resolve_child_payload(data)
    if error:
        return jsonify({"error": error}), status
    child = Child(**fields)
    db.session.add(child)
    db.session.commit()
    return jsonify(serialize_child(child)), 201


@settings_bp.route("/children/<int:child_id>", methods=["PUT"])
def update_child(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404
    data = request.get_json(silent=True) or {}
    fields, error, status = _resolve_child_payload(data)
    if error:
        return jsonify({"error": error}), status
    for key, value in fields.items():
        setattr(child, key, value)
    db.session.commit()
    return jsonify(serialize_child(child))


@settings_bp.route("/children/<int:child_id>", methods=["DELETE"])
def delete_child(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404
    child.active = False
    db.session.commit()
    return jsonify(serialize_child(child))


# ─── System ─────────────────────────────────────────────────────────────────

@settings_bp.route("/system", methods=["GET"])
def get_system():
    return jsonify(serialize_system_config(SystemConfig.query.first()))


@settings_bp.route("/system", methods=["PUT"])
def update_system():
    sc = SystemConfig.query.first()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    roll_number = (data.get("roll_number") or "").strip()
    if not roll_number:
        return jsonify({"error": "Roll number is required"}), 400
    sc.school_name = name
    sc.roll_number = roll_number
    db.session.commit()
    return jsonify(serialize_system_config(sc))
