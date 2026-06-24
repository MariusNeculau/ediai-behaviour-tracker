"""Tests for TherapyGoal / TherapySession — Deliverable 1: goal progress summary."""
import pytest


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def goal_id(app, child_id):
    from models import db, TherapyGoal

    with app.app_context():
        g = TherapyGoal(
            child_id=child_id,
            skill_area="Receptive Language",
            description="Identify 5 objects from a field of 3",
            target_criteria="80% over 3 consecutive sessions",
            status="Active",
        )
        db.session.add(g)
        db.session.commit()
        return g.id


def _add_session(app, child_id, goal_id, status, total=None, correct=None):
    from models import db, TherapySession

    with app.app_context():
        s = TherapySession(
            child_id=child_id,
            goal_id=goal_id,
            status=status,
            total_trials=total,
            correct_trials=correct,
        )
        db.session.add(s)
        db.session.commit()
        return s.id


# ─── serialize_goal progress fields ──────────────────────────────────────────

def test_serialize_goal_zero_progress_when_no_sessions(app, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["completedSessions"] == 0
    assert result["avgAccuracy"] is None


def test_serialize_goal_counts_only_completed_sessions(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    _add_session(app, child_id, goal_id, status="Planned")
    _add_session(app, child_id, goal_id, status="Cancelled")
    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=8)

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["completedSessions"] == 1


def test_serialize_goal_avg_accuracy_single_session(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=8)

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["avgAccuracy"] == 80


def test_serialize_goal_avg_accuracy_multiple_sessions(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=6)   # 60%
    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=10)  # 100%

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["completedSessions"] == 2
    assert result["avgAccuracy"] == 80


def test_serialize_goal_avg_accuracy_ignores_sessions_without_trials(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=7)  # 70%
    _add_session(app, child_id, goal_id, status="Completed", total=None, correct=None)  # no data

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["completedSessions"] == 2   # both count as completed
    assert result["avgAccuracy"] == 70        # only the session with data is averaged


# ─── API endpoint returns progress fields ────────────────────────────────────

def test_list_goals_api_includes_progress_fields(app, client, child_id, goal_id):
    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=9)

    res = client.get("/api/goals")
    assert res.status_code == 200
    goals = res.get_json()
    assert any(g["id"] == goal_id for g in goals)
    goal = next(g for g in goals if g["id"] == goal_id)
    assert "completedSessions" in goal
    assert "avgAccuracy" in goal


def test_list_goals_api_progress_zero_initially(client, goal_id):
    res = client.get("/api/goals")
    goal = next(g for g in res.get_json() if g["id"] == goal_id)
    assert goal["completedSessions"] == 0
    assert goal["avgAccuracy"] is None


def test_list_goals_api_progress_updates_after_session_completed(app, client, child_id, goal_id):
    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=9)

    res = client.get("/api/goals")
    goal = next(g for g in res.get_json() if g["id"] == goal_id)
    assert goal["completedSessions"] == 1
    assert goal["avgAccuracy"] == 90


# ─── Cancel session (Deliverable 2) ──────────────────────────────────────────

def test_cancel_planned_session_returns_cancelled_status(app, client, child_id, goal_id):
    session_id = _add_session(app, child_id, goal_id, status="Planned")

    res = client.put(
        f"/api/therapy-sessions/{session_id}",
        json={"status": "Cancelled"},
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "Cancelled"


def test_cancel_does_not_affect_other_sessions(app, client, child_id, goal_id):
    id_a = _add_session(app, child_id, goal_id, status="Planned")
    id_b = _add_session(app, child_id, goal_id, status="Planned")

    client.put(f"/api/therapy-sessions/{id_a}", json={"status": "Cancelled"})

    res = client.get("/api/therapy-sessions")
    sessions = {s["id"]: s for s in res.get_json()}
    assert sessions[id_a]["status"] == "Cancelled"
    assert sessions[id_b]["status"] == "Planned"


def test_cancel_completed_session_is_accepted_by_api(app, client, child_id, goal_id):
    session_id = _add_session(app, child_id, goal_id, status="Completed", total=10, correct=8)

    res = client.put(
        f"/api/therapy-sessions/{session_id}",
        json={"status": "Cancelled"},
    )
    # API allows it — UI prevents it by not showing the button
    assert res.status_code == 200


def test_cancelled_session_not_counted_in_goal_progress(app, client, child_id, goal_id):
    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=8)
    cancelled_id = _add_session(app, child_id, goal_id, status="Planned")
    client.put(f"/api/therapy-sessions/{cancelled_id}", json={"status": "Cancelled"})

    res = client.get("/api/goals")
    goal = next(g for g in res.get_json() if g["id"] == goal_id)
    assert goal["completedSessions"] == 1
    assert goal["avgAccuracy"] == 80


# ─── Child therapy summary endpoint (Deliverable 3) ──────────────────────────

def test_therapy_summary_unknown_child_returns_404(client):
    res = client.get("/api/children/99999/therapy-summary")
    assert res.status_code == 404


def test_therapy_summary_empty_for_new_child(client, child_id):
    res = client.get(f"/api/children/{child_id}/therapy-summary")
    assert res.status_code == 200
    data = res.get_json()
    assert data["goals"] == []
    assert data["recentSessions"] == []


def test_therapy_summary_includes_goal_with_progress(app, client, child_id, goal_id):
    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=7)

    res = client.get(f"/api/children/{child_id}/therapy-summary")
    data = res.get_json()

    assert len(data["goals"]) == 1
    g = data["goals"][0]
    assert g["skillArea"] == "Receptive Language"
    assert g["completedSessions"] == 1
    assert g["avgAccuracy"] == 70


def test_therapy_summary_recent_sessions_only_completed(app, client, child_id, goal_id):
    _add_session(app, child_id, goal_id, status="Completed", total=10, correct=9)
    _add_session(app, child_id, goal_id, status="Planned")
    _add_session(app, child_id, goal_id, status="Cancelled")

    res = client.get(f"/api/children/{child_id}/therapy-summary")
    data = res.get_json()
    assert len(data["recentSessions"]) == 1
    assert data["recentSessions"][0]["accuracy"] == 90


def test_therapy_summary_recent_sessions_capped_at_five(app, client, child_id, goal_id):
    for i in range(7):
        _add_session(app, child_id, goal_id, status="Completed", total=10, correct=i + 1)

    res = client.get(f"/api/children/{child_id}/therapy-summary")
    data = res.get_json()
    assert len(data["recentSessions"]) == 5


def test_therapy_summary_includes_goal_progress_fields(app, client, child_id, goal_id):
    res = client.get(f"/api/children/{child_id}/therapy-summary")
    data = res.get_json()
    g = data["goals"][0]
    assert "completedSessions" in g
    assert "avgAccuracy" in g


# ─── Therapy in child PDF report (Deliverable 5) ─────────────────────────────

def _make_completed_session(app, child_id, goal_id, total, correct, days_ago=1):
    """Create a Completed TherapySession with conducted_at = today - days_ago."""
    from models import db, TherapySession
    from datetime import datetime, timedelta

    with app.app_context():
        conducted = datetime.utcnow() - timedelta(days=days_ago)
        s = TherapySession(
            child_id=child_id,
            goal_id=goal_id,
            status="Completed",
            total_trials=total,
            correct_trials=correct,
            conducted_at=conducted,
        )
        db.session.add(s)
        db.session.commit()
        return s.id


def test_build_child_report_includes_therapy_data(app, child_id, goal_id):
    from models import db, Child, TherapyGoal
    from reports import build_child_report
    from datetime import date

    _make_completed_session(app, child_id, goal_id, total=10, correct=8, days_ago=2)

    with app.app_context():
        child = db.session.get(Child, child_id)
        goals = TherapyGoal.query.filter_by(child_id=child_id).all()
        report = build_child_report(child, [], "month", date.today(), goals=goals)

    assert len(report["therapy"]) == 1
    t = report["therapy"][0]
    assert t["skill_area"] == "Receptive Language"
    assert t["sessions_count"] == 1
    assert t["avg_accuracy"] == 80


def test_build_child_report_excludes_goals_outside_period(app, child_id, goal_id):
    from models import db, Child, TherapyGoal
    from reports import build_child_report
    from datetime import date

    # Session conducted 40 days ago — outside a "month" (30-day) window
    _make_completed_session(app, child_id, goal_id, total=10, correct=9, days_ago=40)

    with app.app_context():
        child = db.session.get(Child, child_id)
        goals = TherapyGoal.query.filter_by(child_id=child_id).all()
        report = build_child_report(child, [], "month", date.today(), goals=goals)

    assert report["therapy"] == []


def test_build_child_report_no_goals_returns_empty_therapy(app, child_id):
    from models import db, Child
    from reports import build_child_report
    from datetime import date

    with app.app_context():
        child = db.session.get(Child, child_id)
        report = build_child_report(child, [], "month", date.today())

    assert report["therapy"] == []


def test_child_report_pdf_with_therapy_returns_valid_pdf(app, client, child_id, goal_id,
                                                          saved_reports_dir):
    _make_completed_session(app, child_id, goal_id, total=10, correct=7, days_ago=3)

    res = client.get(f"/api/reports/child/{child_id}?period=month")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    pdf_path = saved_reports_dir / data["filename"]
    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:4] == b"%PDF"


def test_child_report_pdf_without_therapy_still_valid(app, client, child_id, saved_reports_dir):
    res = client.get(f"/api/reports/child/{child_id}?period=month")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    pdf_path = saved_reports_dir / data["filename"]
    assert pdf_path.read_bytes()[:4] == b"%PDF"
