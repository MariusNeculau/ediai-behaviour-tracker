from datetime import datetime
from types import SimpleNamespace


def _inc(**kw):
    base = dict(
        occurred_at=datetime(2026, 6, 10, 9, 30),
        child=SimpleNamespace(name="Alice", room=SimpleNamespace(name="Room 1")),
        type="Behavioural", severity="High", trigger="Sensory",
        duration=10, outcome="De-escalated",
        interventions=[SimpleNamespace(name="Calm Space"), SimpleNamespace(name="Sensory Tool")],
        staff=SimpleNamespace(name="Staff Member 1"), status="Resolved",
        description="hit out", notes="follow up",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_incidents_to_csv_header_and_row():
    from exports import incidents_to_csv, CSV_HEADER

    out = incidents_to_csv([_inc()])
    lines = out.strip().split("\n")
    assert lines[0] == ",".join(CSV_HEADER)
    row = lines[1]
    assert "Alice" in row
    assert "Room 1" in row
    assert "Calm Space; Sensory Tool" in row
    assert "Staff Member 1" in row
    assert "2026-06-10" in row and "09:30" in row


def test_incidents_to_csv_empty():
    from exports import incidents_to_csv

    out = incidents_to_csv([])
    assert out.strip().count("\n") == 0   # only the header line
    assert out.startswith("Date,Time,Child")


def test_incidents_to_csv_handles_missing():
    from exports import incidents_to_csv

    inc = _inc(child=None, staff=None, duration=None, interventions=[],
               notes=None, description=None)
    out = incidents_to_csv([inc])
    lines = out.strip().split("\n")
    assert lines[1].count(",") == 13   # 14 columns -> 13 separators, no embedded commas


def test_export_incidents_csv_download(client, saved_reports_dir):
    res = client.get("/api/export/incidents.csv")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["filename"].endswith(".csv")
    text = (saved_reports_dir / body["filename"]).read_text(encoding="utf-8")
    assert text[0] == "﻿"               # UTF-8 BOM for Excel
    assert "Date,Time,Child" in text


def test_export_incidents_csv_includes_row(app, client, child_id, saved_reports_dir):
    from datetime import datetime
    from models import db, Incident

    with app.app_context():
        db.session.add(Incident(
            child_id=child_id, occurred_at=datetime(2026, 6, 10, 9, 30),
            type="Crisis", severity="High",
        ))
        db.session.commit()

    res = client.get("/api/export/incidents.csv")
    body = res.get_json()
    text = (saved_reports_dir / body["filename"]).read_text(encoding="utf-8")
    assert "2026-06-10" in text
    assert "Crisis" in text
