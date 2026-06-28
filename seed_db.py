"""seed_db.py — Populate the demo database with synthetic incidents.

Usage:
    python seed_db.py

Run once after the first deploy, or any time you want to refresh the demo data.
Requires the app to have been started at least once so that seed_lookups() has
already populated rooms, staff, and children.
"""
import random
from datetime import datetime, timedelta

from app import create_app
from models import db, Child, Staff, Incident, Intervention
import config

DESCRIPTIONS = [
    "Pupil became dysregulated during transition between activities.",
    "Challenging behaviour observed during group work.",
    "Physical outburst; de-escalation protocol followed.",
    "Pupil left the classroom without permission.",
    "Distress escalated following an unannounced schedule change.",
    "Repetitive behaviour transitioned to self-injurious action.",
    "Verbal aggression towards staff during morning routine.",
    "Property interference — items knocked off desk deliberately.",
    "Screaming episode triggered by sensory overload in the hallway.",
    "Refusal to comply with structured activity; sat on floor.",
]

NOTES = [
    "Returned to baseline within 15 minutes.",
    "Parents notified. No further intervention needed.",
    "Will review antecedents at next MDT meeting.",
    "Sensory break offered; pupil responded positively.",
    "Peer removed from area as a precaution.",
    "",
    "",
]


def seed():
    app = create_app()
    with app.app_context():
        children = Child.query.filter_by(active=True).all()
        staff_list = Staff.query.filter_by(active=True).all()
        all_interventions = Intervention.query.all()

        if not children:
            print("No children found. Run `python app.py` first to seed lookups, then re-run this script.")
            return

        Incident.query.delete()
        db.session.commit()

        now = datetime.utcnow()
        for _ in range(30):
            child = random.choice(children)
            s = random.choice(staff_list)
            day_offset = random.randint(0, 60)
            hour_offset = random.randint(0, 6)
            occurred = now - timedelta(days=day_offset, hours=hour_offset)

            incident = Incident(
                child_id=child.id,
                staff_id=s.id,
                occurred_at=occurred,
                type=random.choice(config.INCIDENT_TYPES[:-1]),
                severity=random.choice(config.SEVERITY_LEVELS),
                trigger=random.choice(config.TRIGGERS),
                description=random.choice(DESCRIPTIONS),
                duration=random.choice([5, 10, 15, 20, 30]),
                outcome=random.choice(config.OUTCOMES),
                status="Resolved",
                notes=random.choice(NOTES),
            )
            ivs = random.sample(all_interventions, min(random.randint(1, 3), len(all_interventions)))
            incident.interventions = ivs
            db.session.add(incident)

        db.session.commit()
        print("Seeded 30 synthetic demo incidents.")


if __name__ == "__main__":
    seed()
