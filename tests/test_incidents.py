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
