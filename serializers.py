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


def serialize_goal(g):
    completed = [s for s in g.sessions if s.status == "Completed"]
    accuracies = [
        round(s.correct_trials / s.total_trials * 100)
        for s in completed
        if s.total_trials and s.correct_trials is not None
    ]
    avg_accuracy = round(sum(accuracies) / len(accuracies)) if accuracies else None

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
