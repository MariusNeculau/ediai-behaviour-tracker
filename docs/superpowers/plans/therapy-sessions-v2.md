# Plan: Therapy Sessions v2

**Depends on:** `docs/superpowers/specs/therapy-sessions.md` (v1 implemented)  
**Goal:** Close the known limitations of v1 and add goal progress visibility, session history in child profiles, and PDF integration.

---

## Scope

Six discrete deliverables, ordered by value-to-effort ratio:

| # | Deliverable | Effort | Value |
|---|---|---|---|
| 1 | Goal progress summary on Goals table | S | High |
| 2 | Cancel session from UI | XS | Medium |
| 3 | Session history in Child Profile | S | High |
| 4 | Accuracy trend chart per goal | M | High |
| 5 | Therapy sessions in Individual Child PDF | M | High |
| 6 | Incident ↔ session same-day link | L | Medium |

Deliver in order. Each item is independently shippable.

---

## Deliverable 1 — Goal Progress Summary on Goals Table

**What:** Add a progress column to the Goals table showing sessions completed and average accuracy toward the target.

**Example:**
```
Receptive Language | Active | 3 sessions · avg 74% accuracy | [Edit] [Sessions]
```

### Backend change

Add `GET /api/goals/<id>/progress` — or fold into the existing `serialize_goal()`:

```python
def serialize_goal(g):
    sessions = [s for s in g.sessions if s.status == 'Completed']
    completed_count = len(sessions)
    avg_accuracy = None
    if sessions:
        accuracies = [
            round(s.correct_trials / s.total_trials * 100)
            for s in sessions
            if s.total_trials and s.correct_trials is not None
        ]
        avg_accuracy = round(sum(accuracies) / len(accuracies)) if accuracies else None
    return {
        ...existing fields...,
        "completedSessions": completed_count,
        "avgAccuracy": avg_accuracy,
    }
```

### Frontend change

In `renderGoalsTable()`, replace the Description column cell with a two-line cell:

```
Description text (truncated to 40 chars)
3 sessions · avg 74%   ← only if completedSessions > 0
```

**Files:** `serializers.py`, `templates/dashboard.html` (`renderGoalsTable`)  
**Tests:** Add `test_serialize_goal_includes_progress()` in a new `tests/test_sessions.py`

---

## Deliverable 2 — Cancel Session from UI

**What:** Add a **Cancel** button on Planned sessions in the Sessions table.

### Frontend change

In `renderSessionsTable()`, replace the `Complete` button cell:

```javascript
s.status === 'Planned'
  ? `<button onclick="openCompleteSessionModal(${s.id})">Complete</button>
     <button onclick="cancelSession(${s.id})">Cancel</button>`
  : statusBadge
```

```javascript
async function cancelSession(id) {
  if (!confirm('Cancel this session?')) return;
  const res = await fetch(`/api/therapy-sessions/${id}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({status: 'Cancelled'})
  });
  if (!res.ok) { ... }
  const saved = await res.json();
  // update THERAPY_SESSIONS in place
  renderTherapyBody();
}
```

**Files:** `templates/dashboard.html`  
**Tests:** Add `test_cancel_session_returns_cancelled_status()`

---

## Deliverable 3 — Session History in Child Profile

**What:** Add a "Therapy Goals & Sessions" section to `renderChildDetail()`, showing active goals and the last 5 completed sessions.

### Backend change

Add `GET /api/children/<id>/therapy-summary`:

```python
@settings_bp.route("/children/<int:child_id>/therapy-summary", methods=["GET"])
def child_therapy_summary(child_id):
    child = db.session.get(Child, child_id)
    if child is None:
        return jsonify({"error": "Unknown child"}), 404

    goals = TherapyGoal.query.filter_by(child_id=child_id).all()
    recent_sessions = (
        TherapySession.query
        .filter_by(child_id=child_id, status='Completed')
        .order_by(TherapySession.conducted_at.desc())
        .limit(5)
        .all()
    )
    return jsonify({
        "goals": [serialize_goal(g) for g in goals],
        "recentSessions": [serialize_therapy_session(s) for s in recent_sessions],
    })
```

### Frontend change

In `renderChildDetail(id)`, after the Incident History card, add a new card:

```
Therapy Goals & Sessions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Goal: Receptive Language [Active]   3 sessions · avg 74%
  Last session: 20 Jun 2026 · Gestural · 8/10 (80%) · "Good engagement"
Goal: Expressive Language [Active]  1 session · avg 60%
  Last session: 18 Jun 2026 · Verbal · 6/10 (60%)
```

Load data via the new endpoint in `showChildDetail()` — fetch async and inject into the pre-rendered placeholder.

**Files:** `settings_api.py`, `serializers.py`, `templates/dashboard.html`  
**Tests:** `test_child_therapy_summary_endpoint()`

---

## Deliverable 4 — Accuracy Trend Chart per Goal

**What:** When a supervisor clicks **Sessions** on a goal row, show a small sparkline-style bar chart above the sessions table — one bar per completed session in chronological order.

### No backend change needed

Data is already in `THERAPY_SESSIONS`. Filter client-side:

```javascript
function renderAccuracyTrend(goalId) {
  const sessions = THERAPY_SESSIONS
    .filter(s => s.goalId === goalId && s.status === 'Completed' && s.accuracy != null)
    .sort((a, b) => (a.conductedAt || '').localeCompare(b.conductedAt || ''));

  if (sessions.length < 2) return ''; // not enough data to trend

  const max = Math.max(...sessions.map(s => s.accuracy), 1);
  const bars = sessions.map((s, i) => `
    <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
      <div style="font-size:10px;color:var(--gray-700)">${s.accuracy}%</div>
      <div style="width:28px;background:var(--gray-200);border-radius:4px;height:60px;display:flex;align-items:flex-end">
        <div style="width:100%;background:var(--accent);border-radius:4px;height:${Math.round(s.accuracy/max*100)}%"></div>
      </div>
      <div style="font-size:10px;color:var(--gray-500)">${(s.conductedAt||'').slice(5,10)}</div>
    </div>`).join('');

  return `
    <div class="card" style="margin-bottom:14px">
      <div class="card-header"><div class="card-title">Accuracy Trend</div></div>
      <div style="display:flex;gap:8px;align-items:flex-end;padding:14px 18px;overflow-x:auto">${bars}</div>
    </div>`;
}
```

Inject above the sessions table in `renderSessionsTable(filterGoalId)`.

**Files:** `templates/dashboard.html`  
**Tests:** Visual only — no backend change.

---

## Deliverable 5 — Therapy Sessions in Individual Child PDF

**What:** Add a "Therapy Progress" section to the Individual Child PDF report, showing goals and session summary.

### Backend change — `reports.py`

In `build_child_report()`, add therapy data:

```python
from models import TherapyGoal, TherapySession

def build_child_report(child_id, period_start):
    ...existing logic...

    goals = TherapyGoal.query.filter_by(child_id=child_id).all()
    therapy_data = []
    for g in goals:
        completed = [s for s in g.sessions if s.status == 'Completed'
                     and s.conducted_at and s.conducted_at >= period_start]
        if not completed:
            continue
        accuracies = [
            round(s.correct_trials / s.total_trials * 100)
            for s in completed
            if s.total_trials
        ]
        therapy_data.append({
            "skill_area": g.skill_area,
            "description": g.description,
            "target_criteria": g.target_criteria,
            "status": g.status,
            "sessions_count": len(completed),
            "avg_accuracy": round(sum(accuracies) / len(accuracies)) if accuracies else None,
        })

    return {
        ...existing keys...,
        "therapy": therapy_data,
    }
```

In `render_report_pdf()`, add a new section after Pattern Analysis:

```python
if data.get("therapy"):
    # Section header
    # Table: Skill Area | Sessions | Avg Accuracy | Status
    for t in data["therapy"]:
        ...row...
```

**Files:** `reports.py`  
**Tests:** `test_child_report_pdf_includes_therapy_section()`

---

## Deliverable 6 — Incident ↔ Session Same-Day Link

**What:** In the incident modal, if the child had therapy sessions on the same day, show a note: "1 therapy session recorded this day — Receptive Language (74%)."  
In the session completion modal, if the child had incidents on the same day, show: "⚠ 2 incidents recorded on this date."

This is a correlation hint — no new data stored, just a read-time join.

### Frontend change only

In `showIncidentModal(id)`:

```javascript
const sameDaySessions = THERAPY_SESSIONS.filter(s =>
  s.childId === i.childId &&
  s.status === 'Completed' &&
  s.conductedAt && s.conductedAt.startsWith(i.date)
);
```

In `openCompleteSessionModal(id)`:

```javascript
const sessionDate = document.getElementById('cs-date').value.slice(0, 10);
const sameDayIncidents = INCIDENTS.filter(inc =>
  inc.childId === s.childId && inc.date === sessionDate
);
```

Show a subtle info banner inside each modal if the arrays are non-empty.

**Files:** `templates/dashboard.html`  
**Tests:** Visual / integration only.

---

## Delivery Sequence

```
Week 1:  Deliverable 1 (progress summary) + Deliverable 2 (cancel)
Week 2:  Deliverable 3 (child profile section)
Week 3:  Deliverable 4 (accuracy trend chart)
Week 4:  Deliverable 5 (PDF integration)
Week 5:  Deliverable 6 (incident ↔ session link) — optional, defer if deprioritised
```

Each deliverable ships independently with its own tests. No deliverable requires a DB migration beyond what `db.create_all()` handles automatically.

---

## Test File

All new tests go in `tests/test_sessions.py`. Suggested fixture:

```python
@pytest.fixture
def goal_id(app, child_id):
    from models import db, TherapyGoal
    with app.app_context():
        g = TherapyGoal(
            child_id=child_id,
            skill_area="Receptive Language",
            description="Test goal",
            status="Active",
        )
        db.session.add(g)
        db.session.commit()
        return g.id
```
