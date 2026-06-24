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
