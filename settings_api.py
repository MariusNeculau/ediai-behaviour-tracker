"""settings_api.py — CRUD blueprint for the managed entities.

Registered under /api by app.create_app(). Covers Rooms, Staff, and Children.
Deletion is soft (active=False). Archiving an entity that is still in use
(a Room with active children, or a Staff who is an active key worker) is
refused with HTTP 409 and an actionable message.
"""

from flask import Blueprint, jsonify, request

import config
from models import db, Child, Staff, Room
from serializers import serialize_room, serialize_staff, serialize_child

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
