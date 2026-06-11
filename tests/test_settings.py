import config


def test_room_model_and_child_fk(app):
    from models import db, Child, Room

    with app.app_context():
        # Rooms are seeded from config.ROOMS by create_app()
        assert Room.query.count() == len(config.ROOMS)
        room = Room.query.filter_by(name="Room 1").first()
        assert room is not None and room.active is True

        c = Child(name="X", room_id=room.id, support="High")
        db.session.add(c)
        db.session.commit()

        got = db.session.get(Child, c.id)
        assert got.room.name == "Room 1"
        assert got.active is True


def test_serialize_child_includes_ids(app):
    from serializers import serialize_child
    from models import db, Child, Room, Staff

    with app.app_context():
        room = Room.query.filter_by(name="Room 1").first()
        kw = Staff.query.filter_by(name="Staff Member 1").first()
        c = Child(name="Z", room_id=room.id, key_worker_id=kw.id, support="Low")
        db.session.add(c)
        db.session.commit()

        out = serialize_child(c)
        assert out["roomId"] == room.id
        assert out["keyWorkerId"] == kw.id
        assert out["room"] == "Room 1"
        assert out["active"] is True


def test_create_and_list_room(client):
    res = client.post("/api/rooms", json={"name": "Room X"})
    assert res.status_code == 201
    assert res.get_json()["name"] == "Room X"
    names = [r["name"] for r in client.get("/api/rooms").get_json()]
    assert "Room X" in names


def test_create_room_duplicate_returns_400(client):
    client.post("/api/rooms", json={"name": "Dup"})
    res = client.post("/api/rooms", json={"name": "Dup"})
    assert res.status_code == 400


def test_create_room_blank_returns_400(client):
    res = client.post("/api/rooms", json={"name": "   "})
    assert res.status_code == 400


def test_rename_room(client):
    rid = client.post("/api/rooms", json={"name": "Old"}).get_json()["id"]
    res = client.put(f"/api/rooms/{rid}", json={"name": "New"})
    assert res.status_code == 200
    assert res.get_json()["name"] == "New"


def test_archive_empty_room(client):
    rid = client.post("/api/rooms", json={"name": "Empty"}).get_json()["id"]
    res = client.delete(f"/api/rooms/{rid}")
    assert res.status_code == 200
    names = [r["name"] for r in client.get("/api/rooms").get_json()]
    assert "Empty" not in names


def test_archive_room_in_use_returns_409(app, client, room_id):
    from models import db, Child

    with app.app_context():
        db.session.add(Child(name="Kid", room_id=room_id, support="High"))
        db.session.commit()
    res = client.delete(f"/api/rooms/{room_id}")
    assert res.status_code == 409


def test_create_and_list_staff(client):
    res = client.post("/api/staff", json={"name": "New Teacher", "role": "Teacher"})
    assert res.status_code == 201
    names = [s["name"] for s in client.get("/api/staff").get_json()]
    assert "New Teacher" in names


def test_create_staff_duplicate_returns_400(client):
    # "Staff Member 1" is seeded from config
    res = client.post("/api/staff", json={"name": "Staff Member 1"})
    assert res.status_code == 400


def test_edit_staff(client):
    sid = client.post("/api/staff", json={"name": "Temp"}).get_json()["id"]
    res = client.put(f"/api/staff/{sid}", json={"name": "Temp", "role": "SNA"})
    assert res.status_code == 200
    assert res.get_json()["role"] == "SNA"


def test_archive_staff_without_children(client):
    sid = client.post("/api/staff", json={"name": "Lonely"}).get_json()["id"]
    res = client.delete(f"/api/staff/{sid}")
    assert res.status_code == 200


def test_archive_staff_keyworker_returns_409(app, client, room_id, staff_id):
    from models import db, Child

    with app.app_context():
        db.session.add(
            Child(name="Kid", room_id=room_id, support="High", key_worker_id=staff_id)
        )
        db.session.commit()
    res = client.delete(f"/api/staff/{staff_id}")
    assert res.status_code == 409
