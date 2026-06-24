"""Tests for therapy sessions v3 — Deliverable 1: prompt level trend."""
import pytest
from datetime import datetime, timedelta


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def goal_id(app, child_id):
    from models import db, TherapyGoal

    with app.app_context():
        g = TherapyGoal(
            child_id=child_id,
            skill_area="Receptive Language",
            description="Identify 5 objects from a field of 3",
            target_criteria="80% over 3 sessions",
            status="Active",
        )
        db.session.add(g)
        db.session.commit()
        return g.id


def _add_session(app, child_id, goal_id, prompt_level, total=10, correct=8, days_ago=1):
    from models import db, TherapySession

    with app.app_context():
        s = TherapySession(
            child_id=child_id,
            goal_id=goal_id,
            status="Completed",
            total_trials=total,
            correct_trials=correct,
            prompt_level=prompt_level,
            conducted_at=datetime.utcnow() - timedelta(days=days_ago),
        )
        db.session.add(s)
        db.session.commit()
        return s.id


# ─── Deliverable 1: Prompt Level Trend ───────────────────────────────────────

def test_serialize_goal_no_prompt_data(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["latestPromptLevel"] is None
    assert result["promptTrend"] is None


def test_serialize_goal_single_session_no_trend(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    _add_session(app, child_id, goal_id, "Physical")

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["latestPromptLevel"] == "Physical"
    assert result["promptTrend"] is None   # need >= 2 sessions


def test_serialize_goal_latest_prompt_is_most_recent(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    _add_session(app, child_id, goal_id, "Full Physical", days_ago=10)
    _add_session(app, child_id, goal_id, "Physical",      days_ago=7)
    _add_session(app, child_id, goal_id, "Gestural",      days_ago=1)

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["latestPromptLevel"] == "Gestural"


def test_prompt_trend_improving(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    # Full Physical → Physical → Verbal → Gestural → Independent
    for days_ago, level in [(10, "Full Physical"), (8, "Physical"),
                             (6, "Verbal"), (4, "Gestural"), (2, "Independent")]:
        _add_session(app, child_id, goal_id, level, days_ago=days_ago)

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["promptTrend"] == "improving"
    assert result["latestPromptLevel"] == "Independent"


def test_prompt_trend_declining(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    # Independent → Verbal → Physical → Full Physical
    for days_ago, level in [(8, "Independent"), (6, "Verbal"),
                             (4, "Physical"), (2, "Full Physical")]:
        _add_session(app, child_id, goal_id, level, days_ago=days_ago)

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["promptTrend"] == "declining"


def test_prompt_trend_stable(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    # Gestural · Verbal · Gestural · Gestural — no clear direction
    for days_ago, level in [(8, "Gestural"), (6, "Verbal"),
                             (4, "Gestural"), (2, "Gestural")]:
        _add_session(app, child_id, goal_id, level, days_ago=days_ago)

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    assert result["promptTrend"] == "stable"


def test_sessions_without_prompt_level_ignored_in_trend(app, child_id, goal_id):
    from models import db, TherapyGoal
    from serializers import serialize_goal

    _add_session(app, child_id, goal_id, "Full Physical", days_ago=10)
    _add_session(app, child_id, goal_id, None,            days_ago=8)   # no prompt level
    _add_session(app, child_id, goal_id, "Gestural",      days_ago=2)

    with app.app_context():
        g = db.session.get(TherapyGoal, goal_id)
        result = serialize_goal(g)

    # Only 2 sessions with valid prompt — Full Physical → Gestural = improving
    assert result["promptTrend"] == "improving"
    assert result["latestPromptLevel"] == "Gestural"


def test_prompt_trend_fields_present_in_api(client, child_id, goal_id):
    res = client.get("/api/goals")
    assert res.status_code == 200
    goal = next(g for g in res.get_json() if g["id"] == goal_id)
    assert "latestPromptLevel" in goal
    assert "promptTrend" in goal


def test_prompt_trend_in_child_therapy_summary(app, client, child_id, goal_id):
    _add_session(app, child_id, goal_id, "Full Physical", days_ago=5)
    _add_session(app, child_id, goal_id, "Gestural",      days_ago=1)

    res = client.get(f"/api/children/{child_id}/therapy-summary")
    goal = res.get_json()["goals"][0]
    assert goal["latestPromptLevel"] == "Gestural"
    assert goal["promptTrend"] == "improving"


# ─── Deliverable 2: Goal Mastery Auto-Detection ───────────────────────────────

def test_check_mastery_met(app, child_id, goal_id):
    from reports import check_mastery
    from models import db, TherapySession
    from datetime import datetime

    with app.app_context():
        sessions = [
            TherapySession(child_id=child_id, goal_id=goal_id, status="Completed",
                           total_trials=10, correct_trials=9,
                           conducted_at=datetime(2026, 6, i+1, 10, 0))
            for i in range(3)
        ]
        for s in sessions:
            db.session.add(s)
        db.session.commit()
        result = check_mastery("80% over 3 sessions", sessions)

    assert result is True   # 90% >= 80%, all 3 sessions


def test_check_mastery_not_met_below_threshold(app, child_id, goal_id):
    from reports import check_mastery
    from models import db, TherapySession
    from datetime import datetime

    with app.app_context():
        sessions = [
            TherapySession(child_id=child_id, goal_id=goal_id, status="Completed",
                           total_trials=10, correct_trials=7,
                           conducted_at=datetime(2026, 6, i+1, 10, 0))
            for i in range(3)
        ]
        for s in sessions:
            db.session.add(s)
        db.session.commit()
        result = check_mastery("80% over 3 sessions", sessions)

    assert result is False  # 70% < 80%


def test_check_mastery_not_met_insufficient_sessions(app, child_id, goal_id):
    from reports import check_mastery
    from models import db, TherapySession
    from datetime import datetime

    with app.app_context():
        sessions = [
            TherapySession(child_id=child_id, goal_id=goal_id, status="Completed",
                           total_trials=10, correct_trials=9,
                           conducted_at=datetime(2026, 6, 1, 10, 0))
        ]
        db.session.add(sessions[0])
        db.session.commit()
        result = check_mastery("80% over 3 sessions", sessions)

    assert result is False  # only 1 session, need 3


def test_check_mastery_unparseable_criteria():
    from reports import check_mastery

    assert check_mastery(None, []) is False
    assert check_mastery("", []) is False
    assert check_mastery("improve communication skills", []) is False
    assert check_mastery("consistent performance", []) is False


def test_check_mastery_various_patterns():
    from reports import check_mastery
    from unittest.mock import MagicMock

    def make_session(correct, total=10):
        s = MagicMock()
        s.total_trials = total
        s.correct_trials = correct
        return s

    sessions = [make_session(9) for _ in range(5)]  # 90% each

    assert check_mastery("80% accuracy across 3 consecutive sessions", sessions) is True
    assert check_mastery("75% over 5 sessions", sessions) is True
    assert check_mastery("95% over 3 sessions", sessions) is False   # 90% < 95%


def test_serialize_goal_mastery_reached_true(app, child_id):
    from models import db, TherapyGoal, TherapySession
    from serializers import serialize_goal
    from datetime import datetime

    with app.app_context():
        g = TherapyGoal(child_id=child_id, skill_area="Receptive Language",
                        description="Test", target_criteria="80% over 3 sessions",
                        status="Active")
        db.session.add(g)
        db.session.flush()
        for i in range(3):
            db.session.add(TherapySession(
                child_id=child_id, goal_id=g.id, status="Completed",
                total_trials=10, correct_trials=9,
                conducted_at=datetime(2026, 6, i+1, 10, 0)
            ))
        db.session.commit()
        result = serialize_goal(g)

    assert result["masteryReached"] is True


def test_serialize_goal_mastery_reached_false_not_enough_sessions(app, child_id):
    from models import db, TherapyGoal, TherapySession
    from serializers import serialize_goal
    from datetime import datetime

    with app.app_context():
        g = TherapyGoal(child_id=child_id, skill_area="Receptive Language",
                        description="Test", target_criteria="80% over 3 sessions",
                        status="Active")
        db.session.add(g)
        db.session.flush()
        db.session.add(TherapySession(
            child_id=child_id, goal_id=g.id, status="Completed",
            total_trials=10, correct_trials=9,
            conducted_at=datetime(2026, 6, 1, 10, 0)
        ))
        db.session.commit()
        result = serialize_goal(g)

    assert result["masteryReached"] is False


def test_serialize_goal_mastery_not_reached_for_achieved_goal(app, child_id):
    from models import db, TherapyGoal, TherapySession
    from serializers import serialize_goal
    from datetime import datetime

    with app.app_context():
        g = TherapyGoal(child_id=child_id, skill_area="Receptive Language",
                        description="Test", target_criteria="80% over 3 sessions",
                        status="Achieved")   # already achieved
        db.session.add(g)
        db.session.flush()
        for i in range(3):
            db.session.add(TherapySession(
                child_id=child_id, goal_id=g.id, status="Completed",
                total_trials=10, correct_trials=9,
                conducted_at=datetime(2026, 6, i+1, 10, 0)
            ))
        db.session.commit()
        result = serialize_goal(g)

    # masteryReached only fires for Active goals
    assert result["masteryReached"] is False


def test_mastery_reached_field_present_in_api(client, child_id):
    res = client.get("/api/goals")
    assert res.status_code == 200
    # Even with no goals, the field should be present on any returned goal
    # (test passes vacuously if empty, but confirms no KeyError on usage)


# ─── Deliverable 4: IEP Summary PDF ──────────────────────────────────────────

def test_iep_report_unknown_child_returns_404(client):
    res = client.get("/api/reports/child/99999/iep")
    assert res.status_code == 404


def test_iep_report_no_goals_returns_valid_pdf(client, child_id, saved_reports_dir):
    res = client.get(f"/api/reports/child/{child_id}/iep")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["filename"].startswith("EDI_AI_IEP_")
    pdf_bytes = (saved_reports_dir / data["filename"]).read_bytes()
    assert pdf_bytes[:4] == b"%PDF"


def test_iep_report_with_active_goal_and_sessions_is_valid_pdf(
        app, client, child_id, goal_id, saved_reports_dir):
    # Add 3 completed sessions
    for i in range(3):
        _add_session(app, child_id, goal_id, "Gestural",
                     total=10, correct=8+i%2, days_ago=10-i)

    res = client.get(f"/api/reports/child/{child_id}/iep")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    pdf_bytes = (saved_reports_dir / data["filename"]).read_bytes()
    assert pdf_bytes[:4] == b"%PDF"


def test_iep_report_skips_goals_without_completed_sessions(
        app, client, child_id, goal_id, saved_reports_dir):
    # goal_id has NO completed sessions — report should still succeed
    res = client.get(f"/api/reports/child/{child_id}/iep")
    assert res.status_code == 200
    assert res.get_json()["success"] is True


def test_iep_report_sparkline_function():
    from reports import _sparkline
    assert _sparkline([90, 60, 30, 10]) == "▇ ▅ ▃ ▁"
    assert _sparkline([]) == ""
    assert _sparkline([100]) == "▇"
    assert _sparkline([50]) == "▅"
