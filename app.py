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
from datetime import date

from flask import Flask, jsonify, render_template

import config
from models import db, Child, Staff, Incident, Intervention


def _serialize_child(c):
    return {
        "id": c.id,
        "name": c.name,
        "room": c.room,
        "age": c.age,
        "support": c.support,
        "keyWorker": c.key_worker.name if c.key_worker else "",
    }


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
    return app


def seed_lookups():
    """Populează tabelele de catalog din config.py dacă sunt goale."""
    if Intervention.query.count() == 0:
        for name in config.INTERVENTIONS:
            db.session.add(Intervention(name=name))
        db.session.commit()

    if Staff.query.count() == 0:
        for s in config.STAFF:
            db.session.add(Staff(name=s["name"], role=s.get("role")))
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
            school=config.SCHOOL,
            config_data=_config_payload(),
            children=[_serialize_child(c) for c in Child.query.all()],
            staff=[{"name": s.name, "role": s.role} for s in Staff.query.all()],
            incidents=[_serialize_incident(i) for i in Incident.query.all()],
            today=today.isoformat(),
            today_display=today.strftime("%a %d %B %Y"),
        )

    @app.route("/api/config")
    def api_config():
        """Expune taxonomiile customizabile către frontend."""
        payload = {"school": config.SCHOOL}
        payload.update(_config_payload())
        return jsonify(payload)

    @app.route("/api/incidents")
    def api_incidents():
        items = Incident.query.order_by(Incident.occurred_at.desc()).all()
        return jsonify(
            [
                {
                    "id": i.id,
                    "child_id": i.child_id,
                    "type": i.type,
                    "severity": i.severity,
                    "trigger": i.trigger,
                    "duration": i.duration,
                    "outcome": i.outcome,
                    "status": i.status,
                    "interventions": [x.name for x in i.interventions],
                    "occurred_at": i.occurred_at.isoformat() if i.occurred_at else None,
                }
                for i in items
            ]
        )


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
