"""
app.py — EDI AI Behaviour Tracker (Local Desktop)
==================================================

Punct de intrare Flask. Inițializează baza de date SQLite, populează tabelele
lookup din `config.py` (la prima rulare) și servește un frontend generic.

Rulare în dezvoltare:
    pip install flask flask-sqlalchemy
    python app.py
apoi deschide http://127.0.0.1:5000/

Pasul de împachetare (.exe cu PyInstaller) urmează mai târziu în roadmap.
"""

import os
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request

import config
from models import db, Child, Staff, Room, Incident, Intervention, SystemConfig
from serializers import serialize_child, serialize_staff, serialize_room, serialize_system_config


def _serialize_incident(i):
    dt = i.occurred_at
    return {
        "id": i.id,
        "childId": i.child_id,
        "date": dt.strftime("%Y-%m-%d") if dt else "",
        "time": dt.strftime("%H:%M") if dt else "",
        "type": i.type,
        "severity": i.severity,
        "trigger": i.trigger,
        "description": i.description,
        "duration": i.duration,
        "interventions": [x.name for x in i.interventions],
        "outcome": i.outcome,
        "staff": i.staff.name if i.staff else "",
        "status": i.status,
        "notes": i.notes,
    }


def _config_payload():
    """Taxonomiile customizabile, trimise către frontend ca un singur obiect."""
    return {
        "rooms": config.ROOMS,
        "incident_types": config.INCIDENT_TYPES,
        "severity_levels": config.SEVERITY_LEVELS,
        "triggers": config.TRIGGERS,
        "interventions": config.INTERVENTIONS,
        "outcomes": config.OUTCOMES,
        "statuses": config.STATUSES,
        "support_levels": config.SUPPORT_LEVELS,
    }


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # Asigură existența folderului instance/ pentru fișierul SQLite
    os.makedirs(config.INSTANCE_DIR, exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_lookups()

    register_routes(app)
    from settings_api import settings_bp
    app.register_blueprint(settings_bp)
    from reports_api import reports_bp
    app.register_blueprint(reports_bp)
    return app


def seed_lookups():
    """Populează tabelele de catalog din config.py dacă sunt goale."""
    if SystemConfig.query.first() is None:
        db.session.add(
            SystemConfig(
                school_name=config.SCHOOL["name"],
                roll_number=config.SCHOOL["roll_number"],
            )
        )
        db.session.commit()

    if Room.query.count() == 0:
        for name in config.ROOMS:
            db.session.add(Room(name=name))
        db.session.commit()

    if Intervention.query.count() == 0:
        for name in config.INTERVENTIONS:
            db.session.add(Intervention(name=name))
        db.session.commit()

    if Staff.query.count() == 0:
        for s in config.STAFF:
            db.session.add(Staff(name=s["name"], role=s.get("role")))
        db.session.commit()

    if config.SEED_DEMO_DATA and Child.query.count() == 0:
        staff_by_name = {s.name: s for s in Staff.query.all()}
        room_by_name = {r.name: r for r in Room.query.all()}
        for d in config.DEMO_CHILDREN:
            room = room_by_name.get(d["room"])
            db.session.add(
                Child(
                    name=d["name"],
                    room_id=room.id if room else None,
                    age=d.get("age"),
                    support=d.get("support"),
                    key_worker=staff_by_name.get(d.get("keyWorker")),
                )
            )
        db.session.commit()


def register_routes(app):

    @app.route("/")
    def dashboard():
        # Frontend generic portat din legacy/index.html. Identitatea școlii și
        # taxonomiile vin din config.py; datele (elevi/staff/incidente) vin din
        # baza de date — goale pe "blank slate".
        today = date.today()
        return render_template(
            "dashboard.html",
            school=serialize_system_config(SystemConfig.query.first()),
            config_data=_config_payload(),
            children=[serialize_child(c) for c in Child.query.filter_by(active=True).all()],
            staff=[serialize_staff(s) for s in Staff.query.filter_by(active=True).all()],
            rooms=[serialize_room(r) for r in Room.query.filter_by(active=True).all()],
            incidents=[_serialize_incident(i) for i in Incident.query.all()],
            today=today.isoformat(),
            today_display=today.strftime("%a %d %B %Y"),
        )

    @app.route("/api/config")
    def api_config():
        """Expune taxonomiile customizabile către frontend."""
        payload = {"school": serialize_system_config(SystemConfig.query.first())}
        payload.update(_config_payload())
        return jsonify(payload)

    @app.route("/api/incidents", methods=["GET"])
    def api_incidents():
        items = Incident.query.order_by(Incident.occurred_at.desc()).all()
        return jsonify([_serialize_incident(i) for i in items])

    @app.route("/api/incidents", methods=["POST"])
    def create_incident():
        data = request.get_json(silent=True) or {}

        # description is required by business rule even though the model column
        # is nullable (other code paths, e.g. tests, may create rows without it).
        required = ["childId", "date", "time", "type", "severity", "description"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": "Missing required fields: " + ", ".join(missing)}), 400

        child = db.session.get(Child, data["childId"])
        if child is None:
            return jsonify({"error": "Unknown childId"}), 400

        if data["type"] not in config.INCIDENT_TYPES:
            return jsonify({"error": "Invalid incident type"}), 400
        if data["severity"] not in config.SEVERITY_LEVELS:
            return jsonify({"error": "Invalid severity"}), 400

        try:
            occurred_at = datetime.strptime(
                f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid date/time"}), 400

        staff = (
            Staff.query.filter_by(name=data.get("staff")).first()
            if data.get("staff")
            else None
        )
        names = data.get("interventions") or []
        interventions = (
            Intervention.query.filter(Intervention.name.in_(names)).all()
            if names
            else []
        )

        incident = Incident(
            child_id=child.id,
            staff_id=staff.id if staff else None,
            occurred_at=occurred_at,
            type=data["type"],
            severity=data["severity"],
            trigger=data.get("trigger"),
            description=data.get("description"),
            duration=data.get("duration"),
            outcome=data.get("outcome"),
            status="Resolved",
            notes=data.get("notes"),
        )
        incident.interventions = interventions
        db.session.add(incident)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Could not save incident"}), 500
        return jsonify(_serialize_incident(incident)), 201


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
