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


def test_render_child_report_pdf_returns_pdf_bytes():
    from reports import render_child_report_pdf

    report = {
        "school": "Test School", "child_name": "Cian M.", "room_name": "Room 1",
        "key_worker": "Staff Member 1", "period_label": "Last 30 days",
        "period_range": "13 May 2026 – 11 Jun 2026", "generated_on": "11 Jun 2026",
        "total_incidents": 1, "per_week_avg": 0.2, "top_severity": "Medium",
        "avg_duration": "10 min",
        "incident_rows": [{"date": "10 Jun 2026", "type": "Behavioural",
                           "severity": "Medium", "trigger": "Sensory", "outcome": "Resolved"}],
        "top_trigger": "Sensory", "top_type": "Behavioural",
        "peak_time": "Morning (before 12:00)",
        "pattern_text": "Most incidents were Behavioural type.",
    }
    out = render_child_report_pdf(report)
    assert isinstance(out, (bytes, bytearray))
    assert out[:4] == b"%PDF"


def test_render_child_report_pdf_empty_state():
    from reports import render_child_report_pdf

    report = {
        "school": "Test School", "child_name": "Empty Kid", "room_name": "—",
        "key_worker": "—", "period_label": "Last 7 days",
        "period_range": "05 Jun 2026 – 11 Jun 2026", "generated_on": "11 Jun 2026",
        "total_incidents": 0, "per_week_avg": 0.0, "top_severity": "—",
        "avg_duration": "N/A", "incident_rows": [], "top_trigger": "—",
        "top_type": "—", "peak_time": "—",
        "pattern_text": "No incidents recorded in this period.",
    }
    out = render_child_report_pdf(report)
    assert out[:4] == b"%PDF"
