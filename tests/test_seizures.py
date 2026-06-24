"""Tests for seizure log — Deliverable 6: CSV export."""
import pytest


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def seizure_incident_id(app, child_id):
    from models import db, Incident, SeizureDetail, Staff
    from datetime import datetime

    with app.app_context():
        staff = Staff.query.first()
        inc = Incident(
            child_id=child_id,
            staff_id=staff.id if staff else None,
            occurred_at=datetime(2026, 6, 20, 10, 15),
            type="Crisis",
            subtype="Epileptic Seizure",
            severity="High",
            description="Tonic-clonic episode in classroom",
            status="Resolved",
        )
        db.session.add(inc)
        db.session.flush()
        sd = SeizureDetail(
            incident_id=inc.id,
            seizure_type="Tonic-Clonic",
            duration_seconds=90,
            recovery_time_minutes=15,
            position_during="Floor",
            emergency_services_called=False,
            protocol_followed=True,
            medication_administered=False,
        )
        db.session.add(sd)
        db.session.commit()
        return inc.id


@pytest.fixture
def non_seizure_incident_id(app, child_id):
    from models import db, Incident
    from datetime import datetime

    with app.app_context():
        inc = Incident(
            child_id=child_id,
            occurred_at=datetime(2026, 6, 21, 9, 0),
            type="Behavioural",
            severity="Medium",
            description="Shouting in class",
            status="Resolved",
        )
        db.session.add(inc)
        db.session.commit()
        return inc.id


# ─── seizures_to_csv (pure function) ─────────────────────────────────────────

def test_seizures_to_csv_header(app, seizure_incident_id):
    from models import db, Incident
    from exports import seizures_to_csv, SEIZURE_CSV_HEADER

    with app.app_context():
        incidents = Incident.query.filter_by(subtype="Epileptic Seizure").all()
        result = seizures_to_csv(incidents)

    first_line = result.splitlines()[0]
    for col in SEIZURE_CSV_HEADER:
        assert col in first_line


def test_seizures_to_csv_row_with_detail(app, seizure_incident_id):
    from models import db, Incident
    from exports import seizures_to_csv

    with app.app_context():
        incidents = Incident.query.filter_by(subtype="Epileptic Seizure").all()
        result = seizures_to_csv(incidents)

    lines = result.splitlines()
    assert len(lines) == 2  # header + 1 row
    data_row = lines[1]
    assert "2026-06-20" in data_row
    assert "10:15" in data_row
    assert "Tonic-Clonic" in data_row
    assert "90" in data_row       # duration_seconds
    assert "15" in data_row       # recovery_time_minutes
    assert "Floor" in data_row
    assert "No" in data_row       # emergency_services_called = False
    assert "Yes" in data_row      # protocol_followed = True


def test_seizures_to_csv_row_without_seizure_detail(app, child_id):
    from models import db, Incident
    from exports import seizures_to_csv
    from datetime import datetime

    with app.app_context():
        inc = Incident(
            child_id=child_id,
            occurred_at=datetime(2026, 6, 22, 11, 0),
            type="Crisis",
            subtype="Epileptic Seizure",
            severity="High",
            description="Observed seizure, no detail recorded",
            status="Resolved",
        )
        db.session.add(inc)
        db.session.commit()
        incidents = Incident.query.filter_by(subtype="Epileptic Seizure").all()
        result = seizures_to_csv(incidents)

    lines = result.splitlines()
    assert len(lines) == 2
    # Fields that rely on SeizureDetail should be empty strings
    data_row = lines[1]
    assert "2026-06-22" in data_row


def test_seizures_to_csv_empty(app):
    from exports import seizures_to_csv

    result = seizures_to_csv([])
    lines = result.splitlines()
    assert len(lines) == 1  # header only


def test_seizures_to_csv_excludes_non_seizure_incidents(app, seizure_incident_id,
                                                          non_seizure_incident_id):
    from models import db, Incident
    from exports import seizures_to_csv

    with app.app_context():
        incidents = Incident.query.filter_by(subtype="Epileptic Seizure").all()
        result = seizures_to_csv(incidents)

    lines = result.splitlines()
    assert len(lines) == 2  # header + 1 seizure row only


# ─── /api/export/seizures.csv endpoint ───────────────────────────────────────

def test_export_seizures_csv_endpoint_returns_success(client, seizure_incident_id,
                                                        saved_reports_dir):
    res = client.get("/api/export/seizures.csv")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["filename"].startswith("EDI_AI_SeizureLog_")
    assert data["filename"].endswith(".csv")


def test_export_seizures_csv_file_saved_to_disk(client, seizure_incident_id, saved_reports_dir):
    res = client.get("/api/export/seizures.csv")
    data = res.get_json()
    csv_path = saved_reports_dir / data["filename"]
    assert csv_path.exists()


def test_export_seizures_csv_file_contains_bom_and_header(client, seizure_incident_id,
                                                             saved_reports_dir):
    res = client.get("/api/export/seizures.csv")
    data = res.get_json()
    csv_path = saved_reports_dir / data["filename"]
    content = csv_path.read_bytes()
    assert content[:3] == b"\xef\xbb\xbf"   # UTF-8 BOM
    assert b"Seizure Type" in content
    assert b"Protocol Followed" in content


def test_export_seizures_csv_empty_when_no_seizures(client, saved_reports_dir):
    res = client.get("/api/export/seizures.csv")
    assert res.status_code == 200
    data = res.get_json()
    csv_path = saved_reports_dir / data["filename"]
    lines = csv_path.read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) == 1  # header only


# ─── PUT /api/incidents/<id>/seizure (Deliverable 1) ─────────────────────────

def test_update_seizure_detail_existing(client, seizure_incident_id):
    res = client.put(
        f"/api/incidents/{seizure_incident_id}/seizure",
        json={"seizureType": "Absence", "durationSeconds": 30},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["seizureType"] == "Absence"
    assert body["durationSeconds"] == 30
    # Fields not in payload stay unchanged
    assert body["recoveryTimeMinutes"] == 15
    assert body["positionDuring"] == "Floor"


def test_update_seizure_detail_patch_semantics(client, seizure_incident_id):
    # Update only one field; all others must be unchanged
    client.put(
        f"/api/incidents/{seizure_incident_id}/seizure",
        json={"protocolFollowed": False},
    )
    res = client.put(
        f"/api/incidents/{seizure_incident_id}/seizure",
        json={"durationSeconds": 120},
    )
    body = res.get_json()
    assert body["durationSeconds"] == 120
    assert body["protocolFollowed"] is False   # from previous call, not reset


def test_update_seizure_detail_creates_if_missing(app, client, child_id):
    from models import db, Incident
    from datetime import datetime

    with app.app_context():
        inc = Incident(
            child_id=child_id,
            occurred_at=datetime(2026, 6, 25, 14, 0),
            type="Crisis",
            subtype="Epileptic Seizure",
            severity="High",
            description="Witnessed seizure, no detail yet",
            status="Resolved",
        )
        db.session.add(inc)
        db.session.commit()
        inc_id = inc.id

    res = client.put(
        f"/api/incidents/{inc_id}/seizure",
        json={"seizureType": "Focal", "durationSeconds": 45},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["seizureType"] == "Focal"
    assert body["durationSeconds"] == 45


def test_update_seizure_detail_sets_subtype_if_missing(app, client, child_id):
    from models import db, Incident
    from datetime import datetime

    with app.app_context():
        inc = Incident(
            child_id=child_id,
            occurred_at=datetime(2026, 6, 26, 9, 0),
            type="Crisis",
            severity="High",
            description="Old incident without subtype",
            status="Resolved",
        )
        db.session.add(inc)
        db.session.commit()
        inc_id = inc.id

    client.put(f"/api/incidents/{inc_id}/seizure", json={"seizureType": "Absence"})

    with app.app_context():
        from models import Incident as Inc
        updated = db.session.get(Inc, inc_id)
        assert updated.subtype == "Epileptic Seizure"


def test_update_seizure_detail_unknown_incident_returns_404(client):
    res = client.put("/api/incidents/99999/seizure", json={"seizureType": "Absence"})
    assert res.status_code == 404


def test_update_seizure_detail_invalid_type_returns_400(client, seizure_incident_id):
    res = client.put(
        f"/api/incidents/{seizure_incident_id}/seizure",
        json={"seizureType": "NotARealType"},
    )
    assert res.status_code == 400


def test_update_seizure_detail_invalid_position_returns_400(client, seizure_incident_id):
    res = client.put(
        f"/api/incidents/{seizure_incident_id}/seizure",
        json={"positionDuring": "Hanging"},
    )
    assert res.status_code == 400


def test_update_seizure_detail_empty_string_clears_field(client, seizure_incident_id):
    res = client.put(
        f"/api/incidents/{seizure_incident_id}/seizure",
        json={"seizureType": ""},
    )
    assert res.status_code == 200
    assert res.get_json()["seizureType"] is None
