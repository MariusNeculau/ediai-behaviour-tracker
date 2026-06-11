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
