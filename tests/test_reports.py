from datetime import date, datetime
from types import SimpleNamespace


def test_period_start_windows():
    from reports import period_start

    today = date(2026, 6, 11)
    assert period_start("week", today) == date(2026, 6, 5)    # today - 6
    assert period_start("month", today) == date(2026, 5, 13)  # today - 29
    assert period_start("term", today) == date(2026, 3, 14)   # today - 89


def test_period_start_invalid_raises():
    import pytest
    from reports import period_start

    with pytest.raises(ValueError):
        period_start("decade", date(2026, 6, 11))


def test_count_dist_orders_by_count_then_label():
    from reports import _count_dist

    assert _count_dist(["B", "A", "A", "B", "C", "B"]) == [("B", 3), ("A", 2), ("C", 1)]
    assert _count_dist([]) == []
    assert _count_dist([None, "", "X"]) == [("X", 1)]


def test_build_child_report_aggregates():
    from reports import build_child_report

    child = SimpleNamespace(
        name="Cian M.", age=8,
        room=SimpleNamespace(name="Room 1"),
        key_worker=SimpleNamespace(name="Staff Member 1"),
    )
    incidents = [  # already sorted desc by occurred_at
        SimpleNamespace(occurred_at=datetime(2026, 6, 10, 9, 0), type="Behavioural",
                        severity="High", trigger="Sensory", outcome="De-escalated", duration=10,
                        interventions=[SimpleNamespace(name="Calm Space"), SimpleNamespace(name="Sensory Tool")]),
        SimpleNamespace(occurred_at=datetime(2026, 6, 9, 14, 0), type="Behavioural",
                        severity="Medium", trigger="Sensory", outcome="Resolved", duration=20,
                        interventions=[SimpleNamespace(name="Calm Space")]),
        SimpleNamespace(occurred_at=datetime(2026, 6, 8, 9, 30), type="Crisis",
                        severity="Medium", trigger="Transition", outcome="Resolved", duration=None,
                        interventions=[]),
    ]
    r = build_child_report(child, incidents, "month", date(2026, 6, 11))

    assert r["child_name"] == "Cian M."
    assert r["age"] == 8
    assert r["room_name"] == "Room 1"
    assert r["key_worker"] == "Staff Member 1"
    assert r["total_incidents"] == 3
    assert r["per_week_avg"] == 0.7
    assert r["top_severity"] == "Medium"
    assert r["avg_duration"] == "15 min"
    assert r["top_trigger"] == "Sensory"
    assert r["top_type"] == "Behavioural"
    assert r["peak_time"].startswith("Morning")
    assert len(r["incident_rows"]) == 3
    assert r["incident_rows"][0]["date"] == "10 Jun 2026"
    assert r["trigger_counts"] == [("Sensory", 2), ("Transition", 1)]
    assert r["behavior_counts"] == [("Behavioural", 2), ("Crisis", 1)]
    assert r["action_counts"] == [("Calm Space", 2), ("Sensory Tool", 1)]


def test_build_child_report_empty():
    from reports import build_child_report

    child = SimpleNamespace(name="Empty Kid", age=None, room=None, key_worker=None)
    r = build_child_report(child, [], "week", date(2026, 6, 11))

    assert r["total_incidents"] == 0
    assert r["per_week_avg"] == 0.0
    assert r["top_severity"] == "—"
    assert r["avg_duration"] == "N/A"
    assert r["room_name"] == "—"
    assert r["key_worker"] == "—"
    assert r["age"] == "—"
    assert r["trigger_counts"] == []
    assert r["behavior_counts"] == []
    assert r["action_counts"] == []
    assert r["pattern_text"] == "No incidents recorded in this period."


def test_render_child_report_pdf_returns_pdf_bytes():
    from reports import render_child_report_pdf

    report = {
        "school": "Test School", "school_roll": "12345B", "child_name": "Cian M.",
        "room_name": "Room 1", "key_worker": "Staff Member 1", "age": 8,
        "period_label": "Last 30 days", "period_range": "13 May 2026 – 11 Jun 2026",
        "generated_on": "11 Jun 2026", "total_incidents": 3, "per_week_avg": 0.7,
        "top_severity": "Medium", "avg_duration": "15 min",
        "incident_rows": [{"date": "10 Jun 2026", "type": "Behavioural",
                           "severity": "Medium", "trigger": "Sensory", "outcome": "Resolved"}],
        "top_trigger": "Sensory", "top_type": "Behavioural",
        "peak_time": "Morning (before 12:00)",
        "pattern_text": "Most incidents were Behavioural type.",
        "trigger_counts": [("Sensory", 2), ("Transition", 1)],
        "behavior_counts": [("Behavioural", 2), ("Crisis", 1)],
        "action_counts": [("Calm Space", 2), ("Sensory Tool", 1)],
    }
    out = render_child_report_pdf(report)
    assert isinstance(out, (bytes, bytearray))
    assert out[:4] == b"%PDF"


def test_render_child_report_pdf_empty_state():
    from reports import render_child_report_pdf

    report = {
        "school": "Test School", "school_roll": "", "child_name": "Empty Kid",
        "room_name": "—", "key_worker": "—", "age": "—",
        "period_label": "Last 7 days", "period_range": "05 Jun 2026 – 11 Jun 2026",
        "generated_on": "11 Jun 2026", "total_incidents": 0, "per_week_avg": 0.0,
        "top_severity": "—", "avg_duration": "N/A", "incident_rows": [],
        "top_trigger": "—", "top_type": "—", "peak_time": "—",
        "pattern_text": "No incidents recorded in this period.",
        "trigger_counts": [], "behavior_counts": [], "action_counts": [],
    }
    out = render_child_report_pdf(report)
    assert out[:4] == b"%PDF"


def test_child_report_pdf_download(client, child_id):
    res = client.get(f"/api/reports/child/{child_id}?period=month")
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert res.data[:4] == b"%PDF"
    cd = res.headers["Content-Disposition"]
    assert "Test_Child" in cd and ".pdf" in cd


def test_child_report_default_period(client, child_id):
    res = client.get(f"/api/reports/child/{child_id}")
    assert res.status_code == 200
    assert res.data[:4] == b"%PDF"


def test_child_report_unknown_child_returns_404(client):
    res = client.get("/api/reports/child/99999")
    assert res.status_code == 404


def test_child_report_invalid_period_returns_400(client, child_id):
    res = client.get(f"/api/reports/child/{child_id}?period=decade")
    assert res.status_code == 400


def test_child_report_with_incident_still_pdf(app, client, child_id):
    from datetime import datetime
    from models import db, Incident

    with app.app_context():
        db.session.add(Incident(
            child_id=child_id, occurred_at=datetime(2026, 6, 11, 9, 30),
            type="Crisis", severity="High", trigger="Sensory",
            outcome="De-escalated", duration=12,
        ))
        db.session.commit()

    res = client.get(f"/api/reports/child/{child_id}?period=term")
    assert res.status_code == 200
    assert res.data[:4] == b"%PDF"


def test_aggregate_shared():
    from reports import _aggregate

    incs = [
        SimpleNamespace(severity="High", duration=10, trigger="Sensory", type="Behavioural",
                        interventions=[], occurred_at=datetime(2026, 6, 10, 9, 0)),
        SimpleNamespace(severity="Medium", duration=None, trigger="Sensory", type="Crisis",
                        interventions=[], occurred_at=datetime(2026, 6, 9, 14, 0)),
    ]
    a = _aggregate(incs, 30)
    assert a["total_incidents"] == 2
    assert a["per_week_avg"] == 0.5
    assert a["top_trigger"] == "Sensory"
    assert a["avg_duration"] == "10 min"
    assert a["pattern_text"].startswith("Most incidents were")


def _mk_inc(child_id, trigger, hour=9, typ="Behavioural", sev="Medium", dur=10):
    return SimpleNamespace(
        child_id=child_id, occurred_at=datetime(2026, 6, 10, hour, 0),
        type=typ, severity=sev, trigger=trigger, outcome="Resolved", duration=dur,
        interventions=[SimpleNamespace(name="Calm Space")],
    )


def test_build_class_report():
    from reports import build_class_report

    room = SimpleNamespace(id=1, name="Room 1")
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1),
            SimpleNamespace(id=11, name="Bob", room_id=1)]
    incidents = [_mk_inc(10, "Sensory"), _mk_inc(10, "Sensory"), _mk_inc(11, "Noise")]
    r = build_class_report(room, kids, incidents, "month", date(2026, 6, 11))

    assert r["report_type"] == "class"
    assert r["subtitle"] == "Class Summary · Room 1"
    assert ["Students", "2"] in r["details_rows"]
    assert r["total_incidents"] == 3
    assert r["breakdown_header"] == ["Student", "Incidents", "Top Trigger"]
    assert r["breakdown_rows"][0] == ["Alice", "2", "Sensory"]
    assert r["breakdown_rows"][1] == ["Bob", "1", "Noise"]


def test_build_class_report_empty():
    from reports import build_class_report

    room = SimpleNamespace(id=1, name="Room 1")
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1)]
    r = build_class_report(room, kids, [], "week", date(2026, 6, 11))

    assert r["total_incidents"] == 0
    assert r["breakdown_rows"] == [["Alice", "0", "—"]]
    assert r["pattern_text"] == "No incidents recorded in this period."


def test_build_school_report():
    from reports import build_school_report

    rooms = [SimpleNamespace(id=1, name="Room 1"), SimpleNamespace(id=2, name="Room 2")]
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1),
            SimpleNamespace(id=11, name="Bob", room_id=2),
            SimpleNamespace(id=12, name="Cara", room_id=2)]
    incidents = [_mk_inc(11, "Noise"), _mk_inc(12, "Noise"), _mk_inc(10, "Sensory")]
    r = build_school_report(rooms, kids, incidents, "term", date(2026, 6, 11))

    assert r["report_type"] == "school"
    assert ["Classes", "2"] in r["details_rows"]
    assert ["Students", "3"] in r["details_rows"]
    assert r["total_incidents"] == 3
    assert r["breakdown_header"] == ["Class", "Students", "Incidents", "Top Trigger"]
    assert r["breakdown_rows"][0] == ["Room 2", "2", "2", "Noise"]
    assert r["breakdown_rows"][1] == ["Room 1", "1", "1", "Sensory"]


def test_render_class_report_pdf():
    from reports import build_class_report, render_report_pdf

    room = SimpleNamespace(id=1, name="Room 1")
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1)]
    incs = [_mk_inc(10, "Sensory")]
    rep = build_class_report(room, kids, incs, "month", date(2026, 6, 11))
    rep["school"] = "Test School"
    rep["school_roll"] = "12345B"
    out = render_report_pdf(rep)
    assert out[:4] == b"%PDF"


def test_render_school_report_pdf():
    from reports import build_school_report, render_report_pdf

    rooms = [SimpleNamespace(id=1, name="Room 1"), SimpleNamespace(id=2, name="Room 2")]
    kids = [SimpleNamespace(id=10, name="Alice", room_id=1)]
    rep = build_school_report(rooms, kids, [], "week", date(2026, 6, 11))
    rep["school"] = "Test School"
    rep["school_roll"] = ""
    out = render_report_pdf(rep)
    assert out[:4] == b"%PDF"
