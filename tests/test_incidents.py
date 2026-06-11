def test_dashboard_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Saplings" not in res.data


def test_incident_has_notes_column(app, child_id):
    from models import db, Incident
    from datetime import datetime

    with app.app_context():
        inc = Incident(
            child_id=child_id,
            occurred_at=datetime(2026, 6, 11, 9, 30),
            type="Crisis",
            severity="High",
            notes="Parent contacted",
        )
        db.session.add(inc)
        db.session.commit()
        fetched = db.session.get(Incident, inc.id)
        assert fetched.notes == "Parent contacted"


def test_demo_children_seeded_when_enabled(monkeypatch, tmp_path):
    import config

    db_file = tmp_path / "seed.db"
    monkeypatch.setattr(config, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{db_file}")
    monkeypatch.setattr(config, "SEED_DEMO_DATA", True)

    import app as app_module
    from models import Child

    application = app_module.create_app()
    with application.app_context():
        assert Child.query.count() == len(config.DEMO_CHILDREN)
        assert Child.query.count() > 0
        # key worker linked to a seeded Staff row
        first = Child.query.first()
        assert first.key_worker is not None


def _valid_payload(child_id):
    return {
        "childId": child_id,
        "date": "2026-06-11",
        "time": "09:30",
        "type": "Crisis",
        "severity": "High",
        "trigger": "Noise",
        "description": "Test incident",
        "duration": 10,
        "outcome": "De-escalated",
        "staff": "Staff Member 1",
        "notes": "Some notes",
        "interventions": ["Calm Space", "Unknown X"],
    }


def test_post_valid_incident_persists(app, client, child_id):
    res = client.post("/api/incidents", json=_valid_payload(child_id))
    assert res.status_code == 201
    body = res.get_json()
    assert body["childId"] == child_id
    assert body["status"] == "Resolved"
    assert body["notes"] == "Some notes"
    assert "Calm Space" in body["interventions"]
    assert "Unknown X" not in body["interventions"]  # unknown ignored

    from models import db, Incident

    with app.app_context():
        inc = db.session.get(Incident, body["id"])
        assert inc is not None
        assert inc.notes == "Some notes"
        assert inc.staff.name == "Staff Member 1"
        assert inc.occurred_at.strftime("%Y-%m-%d %H:%M") == "2026-06-11 09:30"

    listed = client.get("/api/incidents").get_json()
    assert any(x["id"] == body["id"] for x in listed)


def test_post_missing_required_returns_400(client, child_id):
    res = client.post("/api/incidents", json={"childId": child_id, "date": "2026-06-11"})
    assert res.status_code == 400


def test_post_unknown_child_returns_400(client):
    payload = _valid_payload(99999)
    res = client.post("/api/incidents", json=payload)
    assert res.status_code == 400


def test_post_invalid_type_returns_400(client, child_id):
    payload = _valid_payload(child_id)
    payload["type"] = "Bogus"
    res = client.post("/api/incidents", json=payload)
    assert res.status_code == 400


def test_post_invalid_severity_returns_400(client, child_id):
    payload = _valid_payload(child_id)
    payload["severity"] = "Critical"
    res = client.post("/api/incidents", json=payload)
    assert res.status_code == 400


def test_post_invalid_datetime_returns_400(client, child_id):
    payload = _valid_payload(child_id)
    payload["date"] = "not-a-date"
    res = client.post("/api/incidents", json=payload)
    assert res.status_code == 400
