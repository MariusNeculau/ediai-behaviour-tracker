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


def test_build_child_report_aggregates():
    from reports import build_child_report

    child = SimpleNamespace(
        name="Cian M.",
        room=SimpleNamespace(name="Room 1"),
        key_worker=SimpleNamespace(name="Staff Member 1"),
    )
    incidents = [  # already sorted desc by occurred_at
        SimpleNamespace(occurred_at=datetime(2026, 6, 10, 9, 0), type="Behavioural",
                        severity="High", trigger="Sensory", outcome="De-escalated", duration=10),
        SimpleNamespace(occurred_at=datetime(2026, 6, 9, 14, 0), type="Behavioural",
                        severity="Medium", trigger="Sensory", outcome="Resolved", duration=20),
        SimpleNamespace(occurred_at=datetime(2026, 6, 8, 9, 30), type="Crisis",
                        severity="Medium", trigger="Transition", outcome="Resolved", duration=None),
    ]
    r = build_child_report(child, incidents, "month", date(2026, 6, 11))

    assert r["child_name"] == "Cian M."
    assert r["room_name"] == "Room 1"
    assert r["key_worker"] == "Staff Member 1"
    assert r["total_incidents"] == 3
    assert r["per_week_avg"] == 0.7              # 3 / (30/7)
    assert r["top_severity"] == "Medium"         # 2x Medium vs 1x High
    assert r["avg_duration"] == "15 min"         # (10+20)/2
    assert r["top_trigger"] == "Sensory"         # 2x
    assert r["top_type"] == "Behavioural"        # 2x
    assert r["peak_time"].startswith("Morning")  # hours 9, 14, 9 -> Morning x2
    assert len(r["incident_rows"]) == 3
    assert r["incident_rows"][0]["date"] == "10 Jun 2026"


def test_build_child_report_empty():
    from reports import build_child_report

    child = SimpleNamespace(name="Empty Kid", room=None, key_worker=None)
    r = build_child_report(child, [], "week", date(2026, 6, 11))

    assert r["total_incidents"] == 0
    assert r["per_week_avg"] == 0.0
    assert r["top_severity"] == "—"
    assert r["avg_duration"] == "N/A"
    assert r["room_name"] == "—"
    assert r["key_worker"] == "—"
    assert r["pattern_text"] == "No incidents recorded in this period."
