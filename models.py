"""
models.py — EDI AI Behaviour Tracker (Local Desktop)
=====================================================

Modele de date SQLAlchemy pentru SQLite. Structura reproduce fidel array-urile
in-memory din mockup-ul original (`legacy/index.html`):

    CHILDREN   -> Child
    STAFF      -> Staff
    INCIDENTS  -> Incident  (+ tabela de legătură incident_interventions)

Taxonomiile (tipuri, triggere, intervenții etc.) NU sunt hardcodate aici — ele
provin din `config.py` și sunt validate la inserare. Câmpurile de tip categorie
sunt stocate ca text, validate față de listele din config, ceea ce păstrează
sistemul "blank slate" și ușor de customizat.
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# TherapyGoal / TherapySession — structured goal-directed sessions
# ---------------------------------------------------------------------------


# Tabelă de asociere many-to-many: un incident poate avea mai multe intervenții
incident_interventions = db.Table(
    "incident_interventions",
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
    db.Column("intervention_id", db.Integer, db.ForeignKey("intervention.id"), primary_key=True),
)


class SystemConfig(db.Model):
    """Identitatea școlii (nume + roll number). Un singur rând.

    Sursa de adevăr la runtime — seed-uită o singură dată din config.SCHOOL.
    """

    __tablename__ = "system_config"

    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(120), nullable=False)
    roll_number = db.Column(db.String(40), nullable=False)

    def __repr__(self):
        return f"<SystemConfig {self.school_name!r} ({self.roll_number})>"


class Room(db.Model):
    """Clasă / cameră — promovată din string pe Child la entitate proprie."""

    __tablename__ = "room"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    children = db.relationship("Child", back_populates="room")

    def __repr__(self):
        return f"<Room {self.id} {self.name!r}>"


class Child(db.Model):
    """Elev — corespunde array-ului CHILDREN din mockup (l.281)."""

    __tablename__ = "child"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)          # ex: "Cian M."
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    age = db.Column(db.Integer)
    support = db.Column(db.String(20))                        # High | Medium | Low
    key_worker_id = db.Column(db.Integer, db.ForeignKey("staff.id"))

    room = db.relationship("Room", back_populates="children")
    key_worker = db.relationship("Staff", back_populates="children")
    incidents = db.relationship("Incident", back_populates="child", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Child {self.id} {self.name!r} room_id={self.room_id}>"


class Staff(db.Model):
    """Membru al personalului — corespunde array-ului STAFF din mockup (l.302)."""

    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    role = db.Column(db.String(60))                          # Teacher | SNA | ...
    active = db.Column(db.Boolean, nullable=False, default=True)

    children = db.relationship("Child", back_populates="key_worker")
    incidents = db.relationship("Incident", back_populates="staff")

    def __repr__(self):
        return f"<Staff {self.id} {self.name!r}>"


class Intervention(db.Model):
    """Catalog de intervenții — populat din config.INTERVENTIONS la seed."""

    __tablename__ = "intervention"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)

    def __repr__(self):
        return f"<Intervention {self.name!r}>"


class Incident(db.Model):
    """
    Incident comportamental — entitatea centrală, corespunde array-ului
    INCIDENTS din mockup (l.304). Câmpurile categorice sunt text validat
    față de listele din config.py.
    """

    __tablename__ = "incident"

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey("staff.id"))

    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)  # înlocuiește date+time

    type = db.Column(db.String(40), nullable=False)        # config.INCIDENT_TYPES
    subtype = db.Column(db.String(40))                     # e.g. "Epileptic Seizure"
    severity = db.Column(db.String(20), nullable=False)    # config.SEVERITY_LEVELS
    trigger = db.Column(db.String(60))                     # config.TRIGGERS
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)                       # minute
    outcome = db.Column(db.String(60))                     # config.OUTCOMES
    status = db.Column(db.String(20), default="Active")    # config.STATUSES
    notes = db.Column(db.Text)

    child = db.relationship("Child", back_populates="incidents")
    staff = db.relationship("Staff", back_populates="incidents")
    interventions = db.relationship(
        "Intervention",
        secondary=incident_interventions,
        backref="incidents",
    )

    def __repr__(self):
        return f"<Incident {self.id} {self.type}/{self.severity} child={self.child_id}>"


class SeizureDetail(db.Model):
    """Extended epilepsy data for Crisis incidents with subtype 'Epileptic Seizure'.
    One-to-zero-or-one with Incident (enforced by unique constraint on incident_id).
    """

    __tablename__ = "seizure_detail"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(
        db.Integer, db.ForeignKey("incident.id"), nullable=False, unique=True
    )

    seizure_type = db.Column(db.String(60))        # config.SEIZURE_TYPES
    duration_seconds = db.Column(db.Integer)
    recovery_time_minutes = db.Column(db.Integer)
    position_during = db.Column(db.String(40))     # config.SEIZURE_POSITIONS

    emergency_services_called = db.Column(db.Boolean, default=False)
    protocol_followed = db.Column(db.Boolean, default=False)
    medication_administered = db.Column(db.Boolean, default=False)
    medication_name = db.Column(db.String(80))

    post_ictal_notes = db.Column(db.Text)

    incident = db.relationship(
        "Incident", backref=db.backref("seizure_detail", uselist=False)
    )

    def __repr__(self):
        return f"<SeizureDetail incident={self.incident_id} type={self.seizure_type!r}>"


class TherapyGoal(db.Model):
    """Clinical objective set by a supervisor for a specific child."""

    __tablename__ = "therapy_goal"

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("staff.id"))

    skill_area = db.Column(db.String(80), nullable=False)  # config.THERAPY_SKILL_AREAS
    description = db.Column(db.Text, nullable=False)
    target_criteria = db.Column(db.String(200))            # e.g. "80% over 3 sessions"
    status = db.Column(db.String(20), default="Active")    # config.GOAL_STATUSES

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    achieved_at = db.Column(db.DateTime)

    child = db.relationship("Child", backref="goals")
    created_by = db.relationship("Staff", foreign_keys=[created_by_id])
    sessions = db.relationship("TherapySession", back_populates="goal")

    def __repr__(self):
        return f"<TherapyGoal {self.id} {self.skill_area!r} child={self.child_id}>"


class TherapySession(db.Model):
    """A planned or completed structured therapy session linked to a goal."""

    __tablename__ = "therapy_session"

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey("therapy_goal.id"), nullable=False)
    planned_by_id = db.Column(db.Integer, db.ForeignKey("staff.id"))
    conducted_by_id = db.Column(db.Integer, db.ForeignKey("staff.id"))

    planned_at = db.Column(db.DateTime)
    conducted_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="Planned")  # config.SESSION_STATUSES

    total_trials = db.Column(db.Integer)
    correct_trials = db.Column(db.Integer)
    prompt_level = db.Column(db.String(30))               # config.PROMPT_LEVELS
    notes = db.Column(db.Text)

    child = db.relationship("Child", backref="therapy_sessions")
    goal = db.relationship("TherapyGoal", back_populates="sessions")
    planned_by = db.relationship("Staff", foreign_keys=[planned_by_id])
    conducted_by = db.relationship("Staff", foreign_keys=[conducted_by_id])

    def __repr__(self):
        return f"<TherapySession {self.id} {self.status} child={self.child_id}>"
