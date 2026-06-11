"""serializers.py — JSON shapes for the managed entities (Room, Staff, Child).

Kept in a dedicated module so both app.py (dashboard) and settings_api.py
(CRUD blueprint) import them without a circular import.
"""


def serialize_room(r):
    return {"id": r.id, "name": r.name, "active": r.active}


def serialize_staff(s):
    return {"id": s.id, "name": s.name, "role": s.role, "active": s.active}


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
