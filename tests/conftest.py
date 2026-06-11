import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    """A fresh Flask app bound to an isolated temp SQLite file.

    SEED_DEMO_DATA is forced off so tests control their own data.
    Lookups (Staff, Intervention) are still seeded from config by create_app().
    """
    import config

    db_file = tmp_path / "test.db"
    monkeypatch.setattr(config, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{db_file}")
    monkeypatch.setattr(config, "SEED_DEMO_DATA", False)

    import app as app_module

    application = app_module.create_app()
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def child_id(app):
    """Create one child and return its id."""
    from models import db, Child

    with app.app_context():
        c = Child(name="Test Child", room="Room 1", age=8, support="High")
        db.session.add(c)
        db.session.commit()
        return c.id
