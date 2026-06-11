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
