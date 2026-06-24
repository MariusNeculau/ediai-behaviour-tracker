# Spec: Therapy Sessions Module

**Status:** Implemented (v1)  
**Location:** `sessions_api.py`, `models.py` (`TherapyGoal`, `TherapySession`), `templates/dashboard.html` (Therapy Sessions tab)

---

## Purpose

A structured, goal-directed session tracking module separate from the ABA game sessions in EDI V4. Supervisors define clinical objectives for individual children; therapists record results against those objectives. The separation is intentional — game sessions are child-directed and auto-tracked; therapy sessions are clinician-directed and manually recorded.

---

## Roles

| Role | Capability |
|---|---|
| **Supervisor** | Create and edit goals; plan sessions; mark goals as Achieved / Paused |
| **Therapist** | Complete planned sessions (enter trials, accuracy, prompt level, notes) |

The app has no authentication layer yet — role distinction is by workflow convention, not access control.

---

## Data Model

### `TherapyGoal`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `child_id` | FK → `child` | Required |
| `created_by_id` | FK → `staff` | Nullable (supervisor) |
| `skill_area` | String(80) | Must be in `config.THERAPY_SKILL_AREAS` |
| `description` | Text | Required |
| `target_criteria` | String(200) | Optional. e.g. "80% accuracy over 3 consecutive sessions" |
| `status` | String(20) | `Active` \| `Achieved` \| `Paused` \| `Discontinued` |
| `created_at` | DateTime | Auto UTC |
| `achieved_at` | DateTime | Set automatically when status → `Achieved` |

### `TherapySession`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `child_id` | FK → `child` | Required |
| `goal_id` | FK → `therapy_goal` | Required; must belong to same child |
| `planned_by_id` | FK → `staff` | Nullable (supervisor) |
| `conducted_by_id` | FK → `staff` | Nullable (therapist); set at completion |
| `planned_at` | DateTime | Set by supervisor |
| `conducted_at` | DateTime | Set by therapist at completion |
| `status` | String(20) | `Planned` \| `Completed` \| `Cancelled` |
| `total_trials` | Integer | Nullable until completed |
| `correct_trials` | Integer | Nullable until completed |
| `prompt_level` | String(30) | `config.PROMPT_LEVELS` — see below |
| `notes` | Text | Therapist freeform notes |

`accuracy` is not stored — computed as `round(correct_trials / total_trials * 100)` at read time.

### Prompt Levels (ordered, most to least independent)

```
Independent → Gestural → Verbal → Physical → Full Physical
```

### Skill Areas

```
Receptive Language, Expressive Language, Self-Care, Social Skills,
Fine Motor, Gross Motor, Cognitive Skills, Communication
```

---

## API

All endpoints under `/api`. Blueprint: `sessions_bp` registered in `create_app()`.

### Goals

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/goals` | List goals. Filter: `?childId=<int>` |
| `POST` | `/api/goals` | Create goal |
| `PUT` | `/api/goals/<id>` | Update goal. Setting `status=Achieved` auto-sets `achieved_at` |
| `GET` | `/api/goals/<id>/sessions` | List sessions for a specific goal |

**POST `/api/goals` payload:**
```json
{
  "childId": 1,
  "skillArea": "Receptive Language",
  "description": "Identify 5 objects from a field of 3",
  "targetCriteria": "80% accuracy over 3 consecutive sessions",
  "createdById": 2
}
```

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/therapy-sessions` | List sessions. Filter: `?childId=<int>&goalId=<int>` |
| `POST` | `/api/therapy-sessions` | Create planned session |
| `PUT` | `/api/therapy-sessions/<id>` | Update / complete session |

**POST `/api/therapy-sessions` payload:**
```json
{
  "childId": 1,
  "goalId": 3,
  "plannedAt": "2026-06-25T10:00",
  "plannedById": 2
}
```

**PUT `/api/therapy-sessions/<id>` payload (completion):**
```json
{
  "status": "Completed",
  "conductedById": 4,
  "conductedAt": "2026-06-25T10:20",
  "totalTrials": 10,
  "correctTrials": 8,
  "promptLevel": "Gestural",
  "notes": "Child engaged well. Struggled with 'cup' — revisit next session."
}
```

---

## Validation Rules

### Goal creation
- `childId` must reference an active child
- `skillArea` must be in `config.THERAPY_SKILL_AREAS`
- `description` is required
- `createdById` (if provided) must reference an active staff member

### Session creation
- `childId` must reference an active child
- `goalId` must exist and `goal.child_id` must equal `childId` — cross-child assignment is refused (400)
- `plannedAt` must be valid ISO 8601 if provided

### Session completion
- `status` must be in `config.SESSION_STATUSES`
- `promptLevel` (if provided) must be in `config.PROMPT_LEVELS`
- `conductedAt` must be valid ISO 8601 if provided
- Frontend validates `correctTrials <= totalTrials` before submit

---

## UI Flows

### Supervisor: Add Goal
1. Therapy Sessions tab → Goals sub-tab
2. Click **Add Goal**
3. Fill: Child, Skill Area, Description, Target Criteria, Created By
4. Save → goal appears in list with status `Active`

### Supervisor: Plan Session
1. Therapy Sessions tab → Sessions sub-tab (or click **Sessions** on a goal row)
2. Click **Plan Session**
3. Fill: Child → Goal dropdown auto-filters to active goals for that child → Planned Date, Planned By
4. Save → session appears with status `Planned`

### Therapist: Complete Session
1. Sessions sub-tab → find session with status `Planned`
2. Click **Complete**
3. Fill: Conducted By, Date/Time, Total Trials, Correct Trials, Prompt Level, Notes
4. Save → session status changes to `Completed`; accuracy displayed as percentage

### Supervisor: Mark Goal Achieved
1. Goals sub-tab → click **Edit** on a goal
2. Change Status to `Achieved`
3. Save → `achieved_at` is set automatically to current UTC timestamp

---

## Serializer Output

`serialize_therapy_session()` returns:

```json
{
  "id": 7,
  "childId": 1,
  "childName": "Student A",
  "goalId": 3,
  "goalSkillArea": "Receptive Language",
  "plannedById": 2,
  "plannedBy": "Staff Member 1",
  "conductedById": 4,
  "conductedBy": "Staff Member 2",
  "plannedAt": "2026-06-25T10:00:00",
  "conductedAt": "2026-06-25T10:22:00",
  "status": "Completed",
  "totalTrials": 10,
  "correctTrials": 8,
  "accuracy": 80,
  "promptLevel": "Gestural",
  "notes": "Child engaged well."
}
```

---

## Known Limitations (v1)

- No authentication — supervisor vs. therapist distinction is by convention only
- No inline goal progress summary (e.g. "3/5 sessions completed, avg accuracy 74%") — planned for v2
- Sessions cannot be marked `Cancelled` from the UI (API supports it, UI does not expose it yet)
- No link from a completed therapy session back to an incident logged the same day

---

## Planned Enhancements (v2)

- **Goal progress bar** on the Goals table: sessions completed vs. target criteria
- **Accuracy trend chart** per goal: line chart across sessions
- **Cancel session** button in UI
- **Session notes history** in child profile view
- **PDF report inclusion**: therapy session summary in the Individual Child PDF report
