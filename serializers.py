"""serializers.py — JSON shapes for the managed entities (Room, Staff, Child).

Kept in a dedicated module so both app.py (dashboard) and settings_api.py
(CRUD blueprint) import them without a circular import.
"""


def serialize_room(r):
    return {"id": r.id, "name": r.name, "active": r.active}


def serialize_staff(s):
    return {"id": s.id, "name": s.name, "role": s.role, "active": s.active}


def serialize_system_config(sc):
    return {"name": sc.school_name, "roll_number": sc.roll_number}


def serialize_child(c):
    return {
        "id": c.id,
        "name": c.name,
        "room": c.room.name if c.room else "",
        "roomId": c.room_id,
        "age": c.age,
        "support": c.support,
        "keyWorker": c.key_worker.name if c.key_worker else "",
        "keyWorkerId": c.key_worker_id,
        "active": c.active,
    }


def serialize_seizure_incident(i):
    """Incident epileptic + SeizureDetail — folosit de seizure log și child summary."""
    dt = i.occurred_at
    sd = i.seizure_detail
    return {
        "id": i.id,
        "childId": i.child_id,
        "childName": i.child.name if i.child else "",
        "childRoom": i.child.room.name if (i.child and i.child.room) else "",
        "date": dt.strftime("%d %b %Y") if dt else "",
        "time": dt.strftime("%H:%M") if dt else "",
        "seizureType": sd.seizure_type if sd else None,
        "durationSeconds": sd.duration_seconds if sd else None,
        "positionDuring": sd.position_during if sd else None,
        "protocolFollowed": bool(sd.protocol_followed) if sd else False,
        "emergencyServicesCalled": bool(sd.emergency_services_called) if sd else False,
        "medicationAdministered": bool(sd.medication_administered) if sd else False,
        "medicationName": sd.medication_name if sd else None,
        "staff": i.staff.name if i.staff else "",
    }


def serialize_seizure_detail(sd):
    if sd is None:
        return None
    return {
        "seizureType": sd.seizure_type,
        "durationSeconds": sd.duration_seconds,
        "recoveryTimeMinutes": sd.recovery_time_minutes,
        "positionDuring": sd.position_during,
        "emergencyServicesCalled": sd.emergency_services_called,
        "protocolFollowed": sd.protocol_followed,
        "medicationAdministered": sd.medication_administered,
        "medicationName": sd.medication_name,
        "postIctalNotes": sd.post_ictal_notes,
    }


_PROMPT_ORDER = {
    "Independent": 1,
    "Gestural": 2,
    "Verbal": 3,
    "Physical": 4,
    "Full Physical": 5,
}


def serialize_goal(g):
    completed = [s for s in g.sessions if s.status == "Completed"]
    accuracies = [
        round(s.correct_trials / s.total_trials * 100)
        for s in completed
        if s.total_trials and s.correct_trials is not None
    ]
    avg_accuracy = round(sum(accuracies) / len(accuracies)) if accuracies else None

    # Prompt level trend — needs chronological order
    with_prompt = sorted(
        [s for s in completed if s.prompt_level in _PROMPT_ORDER],
        key=lambda s: (s.conducted_at or ""),
    )
    latest_prompt = with_prompt[-1].prompt_level if with_prompt else None

    prompt_trend = None
    if len(with_prompt) >= 2:
        scores = [_PROMPT_ORDER[s.prompt_level] for s in with_prompt]
        half = len(scores) // 2
        avg_first = sum(scores[:half]) / half
        avg_second = sum(scores[half:]) / (len(scores) - half)
        diff = avg_second - avg_first
        if diff < -0.5:
            prompt_trend = "improving"    # moving toward Independent (lower score)
        elif diff > 0.5:
            prompt_trend = "declining"
        else:
            prompt_trend = "stable"

    return {
        "id": g.id,
        "childId": g.child_id,
        "childName": g.child.name if g.child else "",
        "createdById": g.created_by_id,
        "createdBy": g.created_by.name if g.created_by else "",
        "skillArea": g.skill_area,
        "description": g.description,
        "targetCriteria": g.target_criteria,
        "status": g.status,
        "createdAt": g.created_at.isoformat() if g.created_at else None,
        "achievedAt": g.achieved_at.isoformat() if g.achieved_at else None,
        "completedSessions": len(completed),
        "avgAccuracy": avg_accuracy,
        "latestPromptLevel": latest_prompt,
        "promptTrend": prompt_trend,
    }


def serialize_therapy_session(ts):
    accuracy = None
    if ts.total_trials and ts.correct_trials is not None:
        accuracy = round((ts.correct_trials / ts.total_trials) * 100)
    return {
        "id": ts.id,
        "childId": ts.child_id,
        "childName": ts.child.name if ts.child else "",
        "goalId": ts.goal_id,
        "goalSkillArea": ts.goal.skill_area if ts.goal else "",
        "plannedById": ts.planned_by_id,
        "plannedBy": ts.planned_by.name if ts.planned_by else "",
        "conductedById": ts.conducted_by_id,
        "conductedBy": ts.conducted_by.name if ts.conducted_by else "",
        "plannedAt": ts.planned_at.isoformat() if ts.planned_at else None,
        "conductedAt": ts.conducted_at.isoformat() if ts.conducted_at else None,
        "status": ts.status,
        "totalTrials": ts.total_trials,
        "correctTrials": ts.correct_trials,
        "accuracy": accuracy,
        "promptLevel": ts.prompt_level,
        "notes": ts.notes,
    }
