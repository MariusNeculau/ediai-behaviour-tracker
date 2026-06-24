# Plan: Therapy Sessions v3

**Depends on:** `docs/superpowers/plans/therapy-sessions-v2.md` (fully implemented)  
**Goal:** Add clinical depth — prompt level independence tracking, goal mastery detection, session notes history, IEP export, calendar scheduling, and goal templates.

---

## Scope

Six deliverables, ordered by value-to-effort ratio:

| # | Deliverable | Effort | Value |
|---|---|---|---|
| 1 | Prompt level independence trend | S | High |
| 2 | Goal mastery auto-detection | M | High |
| 3 | Session notes history view | S | Medium |
| 4 | IEP Summary PDF export | M | High |
| 5 | Weekly session calendar | L | Medium |
| 6 | Goal templates | M | Medium |

---

## Deliverable 1 — Prompt Level Independence Trend

**What:** Show in the Sessions table and goal progress summary whether the child is becoming more independent over time. In ABA practice, decreasing prompt level is the primary indicator of skill acquisition.

### Prompt level order (most → least independent)

```
1 = Independent
2 = Gestural
3 = Verbal
4 = Physical
5 = Full Physical
```

A downward trend (5 → 3 → 1) means the child is generalising — a clinical milestone.

### Backend change — `serializers.py`

Add `serialize_goal()` computed field `promptTrend`:

```python
PROMPT_ORDER = {
    "Independent": 1, "Gestural": 2, "Verbal": 3,
    "Physical": 4, "Full Physical": 5,
}

def serialize_goal(g):
    completed = [s for s in g.sessions if s.status == "Completed" and s.prompt_level]
    prompt_scores = [PROMPT_ORDER[s.prompt_level] for s in completed
                     if s.prompt_level in PROMPT_ORDER]

    prompt_trend = None
    if len(prompt_scores) >= 2:
        first_half = prompt_scores[:len(prompt_scores)//2]
        second_half = prompt_scores[len(prompt_scores)//2:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        diff = avg_second - avg_first
        if diff < -0.5:
            prompt_trend = "improving"    # becoming more independent
        elif diff > 0.5:
            prompt_trend = "declining"
        else:
            prompt_trend = "stable"

    return {
        ...existing fields...,
        "latestPromptLevel": completed[-1].prompt_level if completed else None,
        "promptTrend": prompt_trend,
    }
```

### Frontend change — Goals table

In `renderGoalsTable()`, add a third line under the progress line:

```
3 sessions · avg 74%
Latest prompt: Gestural  ↑ Improving independence
```

Colours: green for improving, orange for stable, red for declining.

Also shown in `renderTherapySummaryCard()` in Child Profile.

**Files:** `serializers.py`, `templates/dashboard.html`  
**Tests:** `test_prompt_trend_improving()`, `test_prompt_trend_declining()`, `test_prompt_trend_stable()`, `test_prompt_trend_insufficient_data()`

---

## Deliverable 2 — Goal Mastery Auto-Detection

**What:** When a goal's `target_criteria` matches a recognisable pattern, the system checks completed sessions automatically and surfaces a "Ready to Mark Achieved" badge when criteria are met. Supervisor still manually confirms — the system only detects, never auto-changes status.

### Supported pattern (v1 of detection)

Pattern: `"N% [accuracy] [over|across] M [consecutive] sessions"` — case-insensitive.

Examples:
- `"80% over 3 sessions"` → threshold=80, window=3
- `"80% accuracy across 3 consecutive sessions"` → same
- `"75% over 5 sessions"` → threshold=75, window=5

### Backend change — new helper in `reports.py` (pure, no DB)

```python
import re

_MASTERY_RE = re.compile(
    r"(\d+)\s*%.*?(\d+)\s*(?:consecutive\s+)?sessions?",
    re.IGNORECASE,
)

def check_mastery(target_criteria, completed_sessions):
    """Returns True if the last N completed sessions all meet the % threshold."""
    if not target_criteria:
        return False
    m = _MASTERY_RE.search(target_criteria)
    if not m:
        return False
    threshold, window = int(m.group(1)), int(m.group(2))
    recent = [
        s for s in completed_sessions
        if s.total_trials and s.correct_trials is not None
    ][-window:]
    if len(recent) < window:
        return False
    return all(
        round(s.correct_trials / s.total_trials * 100) >= threshold
        for s in recent
    )
```

### Backend change — `serializers.py`

Add `masteryReached` boolean to `serialize_goal()`:

```python
from reports import check_mastery

def serialize_goal(g):
    completed = [s for s in g.sessions if s.status == "Completed"]
    mastery_reached = (
        g.status == "Active" and
        check_mastery(g.target_criteria, completed)
    )
    return {
        ...existing...,
        "masteryReached": mastery_reached,
    }
```

### Frontend change — Goals table

When `g.masteryReached` is true, show a green badge next to the goal status:

```
[Active]  ✓ Ready to Mark Achieved
```

Clicking it opens a confirmation dialog that calls `PUT /api/goals/<id>` with `{status: "Achieved"}`.

**Files:** `reports.py`, `serializers.py`, `templates/dashboard.html`  
**Tests:** `test_check_mastery_met()`, `test_check_mastery_not_met_below_threshold()`, `test_check_mastery_not_met_insufficient_sessions()`, `test_check_mastery_unparseable_criteria()`, `test_serialize_goal_mastery_reached_true()`, `test_serialize_goal_mastery_reached_false()`

---

## Deliverable 3 — Session Notes History View

**What:** When a supervisor clicks **Sessions** on a goal row, show a collapsible "Session Notes" panel above the sessions table — a chronological feed of all notes from completed sessions for that goal.

### No backend change needed

Data is already in `THERAPY_SESSIONS`. Filter client-side:

```javascript
function renderSessionNotes(filterGoalId) {
  const sessions = THERAPY_SESSIONS
    .filter(s => s.goalId === filterGoalId &&
                 s.status === 'Completed' &&
                 s.notes)
    .sort((a, b) => (a.conductedAt || '').localeCompare(b.conductedAt || ''));

  if (!sessions.length) return '';

  const items = sessions.map(s => `
    <div style="padding:10px 0;border-bottom:1px solid var(--gray-200)">
      <div style="font-size:11px;color:var(--gray-500);margin-bottom:4px">
        ${s.conductedAt ? s.conductedAt.slice(0,10) : '—'}
        &nbsp;·&nbsp; ${s.conductedBy || '—'}
        &nbsp;·&nbsp; ${s.promptLevel || '—'}
        &nbsp;·&nbsp; <strong style="color:var(--accent)">${s.accuracy != null ? s.accuracy+'%' : '—'}</strong>
      </div>
      <div style="font-size:13px">${s.notes}</div>
    </div>`).join('');

  return `
    <div class="card" style="margin-bottom:14px">
      <div class="card-header" style="cursor:pointer" onclick="toggleNotesPanel()">
        <div class="card-title">Session Notes (${sessions.length})</div>
        <div id="notes-toggle-icon" style="font-size:18px">▾</div>
      </div>
      <div id="notes-panel" style="padding:0 18px 6px">${items}</div>
    </div>`;
}

function toggleNotesPanel() {
  const panel = document.getElementById('notes-panel');
  const icon = document.getElementById('notes-toggle-icon');
  if (!panel) return;
  const collapsed = panel.style.display === 'none';
  panel.style.display = collapsed ? 'block' : 'none';
  icon.textContent = collapsed ? '▾' : '▸';
}
```

Inject above the sessions table in `renderSessionsTable(filterGoalId)`.

**Files:** `templates/dashboard.html`  
**Tests:** Visual only — no backend change.

---

## Deliverable 4 — IEP Summary PDF Export

**What:** A dedicated PDF report for Individual Education Plan reviews — one page per active goal, showing description, target criteria, session history, accuracy trend, and latest prompt level. Different from the Individual Child report which includes incidents.

### Backend — new function in `reports.py`

```python
def render_iep_pdf(child, goals_with_sessions, school_name, school_roll):
    """
    goals_with_sessions: list of (TherapyGoal, [TherapySession]) tuples,
    pre-filtered to Active goals with at least one Completed session.
    """
```

For each goal:
- Goal header: Skill Area + Description + Target Criteria + Status
- Sessions summary table: Date | Accuracy | Prompt Level | Notes (truncated)
- Accuracy trend (last 6 sessions as text sparkline: ▁▃▅▇)
- Prompt level trend: last 3 levels with direction arrow

### Backend — new endpoint in `reports_api.py`

```python
@reports_bp.route("/reports/child/<int:child_id>/iep", methods=["GET"])
def child_iep_report(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404

    goals = TherapyGoal.query.filter_by(child_id=child_id, status="Active").all()
    pdf = render_iep_pdf(child, goals, sc["name"], sc["roll_number"])
    ...save and return JSON with filename...
```

### Frontend

Add **Generate IEP Report** button next to **Generate Report** in Child Profile header.

**Files:** `reports.py`, `reports_api.py`, `templates/dashboard.html`  
**Tests:** `test_iep_report_returns_pdf()`, `test_iep_report_unknown_child_404()`, `test_iep_report_no_goals_still_valid()`

---

## Deliverable 5 — Weekly Session Calendar

**What:** A weekly calendar view in the Therapy Sessions tab showing planned sessions as blocks on a 5-day (Mon–Fri) grid. Gives supervisors a visual overview of the therapy schedule.

### No backend change needed

Data is already in `THERAPY_SESSIONS`. Filter by current week on the client.

### Frontend — new view in `renderTherapyShell()`

Add a third sub-tab: **Goals | Sessions | Calendar**

```javascript
function renderCalendar() {
  const weekStart = getMonday(new Date());
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
  // For each day, show Planned sessions as coloured blocks
  // Click block → openCompleteSessionModal or view session detail
}

function getMonday(d) {
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(d.setDate(diff));
}
```

Calendar columns = Mon–Fri. Each cell shows:
```
[Child Name]
Skill Area
[Planned | Completed | Cancelled badge]
```

Navigation: **← Previous week** / **Next week →**

**Files:** `templates/dashboard.html`  
**Tests:** Visual only — no backend change.

---

## Deliverable 6 — Goal Templates

**What:** Supervisors can save any goal as a template and apply it to multiple children quickly. Eliminates repetitive typing for common goals (e.g. "Receptive Language: identify 5 objects from a field of 3").

### Backend changes

New model in `models.py`:

```python
class GoalTemplate(db.Model):
    __tablename__ = "goal_template"

    id = db.Column(db.Integer, primary_key=True)
    skill_area = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    target_criteria = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

New endpoints in `sessions_api.py`:

```
GET  /api/goal-templates          list all templates
POST /api/goal-templates          create template
DELETE /api/goal-templates/<id>   delete template
POST /api/goals/from-template     create goal from template (pass childId + templateId)
```

### Frontend

In `openGoalModal(null)`, add a **Use Template** button that opens a template picker dropdown. Selecting a template pre-fills skill area, description, and target criteria. Supervisor still picks the child and can edit the pre-filled values.

**Files:** `models.py`, `sessions_api.py`, `templates/dashboard.html`  
**Tests:** `test_create_goal_template()`, `test_list_goal_templates()`, `test_create_goal_from_template()`, `test_create_goal_from_template_unknown_child_404()`

---

## Delivery Sequence

```
Week 1:  D1 (prompt trend) + D3 (session notes history)
Week 2:  D2 (mastery detection)
Week 3:  D4 (IEP PDF)
Week 4:  D5 (calendar) — most complex frontend
Week 5:  D6 (goal templates) — new model, independent of others
```

---

## Test File

New tests go in `tests/test_therapy_v3.py`. Suggested base fixtures (extend existing conftest):

```python
@pytest.fixture
def completed_session_id(app, child_id, goal_id):
    from models import db, TherapySession
    from datetime import datetime

    with app.app_context():
        s = TherapySession(
            child_id=child_id,
            goal_id=goal_id,
            status="Completed",
            total_trials=10,
            correct_trials=8,
            prompt_level="Gestural",
            conducted_at=datetime.utcnow(),
        )
        db.session.add(s)
        db.session.commit()
        return s.id
```
