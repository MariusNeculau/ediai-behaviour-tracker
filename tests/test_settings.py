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


def test_create_child_valid(client, room_id, staff_id):
    res = client.post(
        "/api/children",
        json={"name": "Alice", "roomId": room_id, "age": 7, "support": "High", "keyWorkerId": staff_id},
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["roomId"] == room_id
    assert body["keyWorkerId"] == staff_id
    assert body["name"] == "Alice"


def test_create_child_unknown_room_returns_400(client):
    res = client.post("/api/children", json={"name": "Bob", "roomId": 99999})
    assert res.status_code == 400


def test_create_child_blank_name_returns_400(client, room_id):
    res = client.post("/api/children", json={"name": "", "roomId": room_id})
    assert res.status_code == 400


def test_update_child_room_preserves_incidents(app, client, child_id):
    from models import db, Incident, Room
    from datetime import datetime

    with app.app_context():
        db.session.add(
            Incident(child_id=child_id, occurred_at=datetime(2026, 6, 11, 9, 30), type="Crisis", severity="High")
        )
        db.session.commit()
        other_room = Room.query.filter_by(name="Room 2").first().id

    res = client.put(f"/api/children/{child_id}", json={"name": "Test Child", "roomId": other_room})
    assert res.status_code == 200
    assert res.get_json()["roomId"] == other_room

    with app.app_context():
        assert Incident.query.filter_by(child_id=child_id).count() == 1


def test_archive_child_keeps_row_and_incidents(app, client, child_id):
    from models import db, Child, Incident
    from datetime import datetime

    with app.app_context():
        db.session.add(
            Incident(child_id=child_id, occurred_at=datetime(2026, 6, 11, 9, 30), type="Crisis", severity="High")
        )
        db.session.commit()

    res = client.delete(f"/api/children/{child_id}")
    assert res.status_code == 200

    active = client.get("/api/children").get_json()
    assert all(c["id"] != child_id for c in active)
    archived = client.get("/api/children?all=1").get_json()
    assert any(c["id"] == child_id for c in archived)

    with app.app_context():
        assert db.session.get(Child, child_id) is not None
        assert Incident.query.filter_by(child_id=child_id).count() == 1


def test_system_config_seeded_from_config(app):
    import config
    from serializers import serialize_system_config
    from models import SystemConfig

    with app.app_context():
        sc = SystemConfig.query.first()
        assert sc is not None
        assert SystemConfig.query.count() == 1
        out = serialize_system_config(sc)
        assert out["name"] == config.SCHOOL["name"]
        assert out["roll_number"] == config.SCHOOL["roll_number"]


def test_get_system_config_defaults(client):
    import config

    body = client.get("/api/system").get_json()
    assert body["name"] == config.SCHOOL["name"]
    assert body["roll_number"] == config.SCHOOL["roll_number"]


def test_update_system_config(client):
    res = client.put("/api/system", json={"name": "Oak Primary", "roll_number": "12345B"})
    assert res.status_code == 200
    assert res.get_json() == {"name": "Oak Primary", "roll_number": "12345B"}

    body = client.get("/api/system").get_json()
    assert body["name"] == "Oak Primary"
    assert body["roll_number"] == "12345B"


def test_update_system_blank_name_returns_400(client):
    res = client.put("/api/system", json={"name": "   ", "roll_number": "12345B"})
    assert res.status_code == 400


def test_update_system_blank_roll_returns_400(client):
    res = client.put("/api/system", json={"name": "Oak Primary", "roll_number": ""})
    assert res.status_code == 400


def test_dashboard_reflects_system_config(client):
    client.put("/api/system", json={"name": "Maple Special School", "roll_number": "99999Z"})
    html = client.get("/").get_data(as_text=True)
    assert "Maple Special School" in html


def test_api_config_reflects_system_config(client):
    client.put("/api/system", json={"name": "Birch College", "roll_number": "55555X"})
    body = client.get("/api/config").get_json()
    assert body["school"]["name"] == "Birch College"
    assert body["school"]["roll_number"] == "55555X"
