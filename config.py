"""
config.py — EDI AI Behaviour Tracker (Local Desktop)
=====================================================

Configurare centrală a aplicației. TOATE datele specifice unei școli sau ale
unei taxonomii de comportamente au fost extrase aici din mockup-ul original
(`legacy/index.html`), astfel încât aplicația să rămână un "blank slate"
complet customizabil.

>>> CUM PERSONALIZEZI <<<
Înlocuiește valorile din SCHOOL, ROOMS și STAFF cu cele ale școlii tale.
Categoriile (INCIDENT_TYPES, SEVERITY_LEVELS, TRIGGERS, INTERVENTIONS,
OUTCOMES, STATUSES, SUPPORT_LEVELS) reflectă vocabularul SEN irlandez folosit
în mockup — modifică-le după nevoie. La prima rulare, `app.py` populează baza
de date SQLite din aceste valori (seed), dacă tabela respectivă e goală.
"""

# ---------------------------------------------------------------------------
# 1. IDENTITATEA ȘCOLII  (extras din index.html — l.6/254/954/958)
#    ÎNLOCUIEȘTE aceste valori. Mockup-ul folosea "Saplings Special School".
# ---------------------------------------------------------------------------
SCHOOL = {
    "name": "Your School Name",          # era: "Saplings Special School"
    "roll_number": "00000A",             # era: "19876W"
    "country": "Ireland",
}

# ---------------------------------------------------------------------------
# 2. CLASE / CAMERE  (extras din index.html — l.943)
#    Listă plată de nume de clase. Sunt referite de fiecare elev.
# ---------------------------------------------------------------------------
ROOMS = [
    "Room 1",
    "Room 2",
    "Room 3",
    "Room 4",
    "Room 5",
]

# ---------------------------------------------------------------------------
# 3. PERSONAL / STAFF  (extras din index.html — l.302)
#    Erau nume reale în mockup. Înlocuiește-le cu personalul real ulterior.
#    `key_worker` din mockup mapează pe câmpul `name` de aici.
# ---------------------------------------------------------------------------
STAFF = [
    {"name": "Staff Member 1", "role": "Teacher"},
    {"name": "Staff Member 2", "role": "Teacher"},
    {"name": "Staff Member 3", "role": "Teacher"},
    {"name": "Staff Member 4", "role": "SNA"},
    {"name": "Staff Member 5", "role": "SNA"},
]

# ---------------------------------------------------------------------------
# 4. TAXONOMIA COMPORTAMENTELOR  (extras din index.html)
#    Acestea sunt categoriile "hardcodate" în mockup. Le ținem ca liste
#    simple ca să fie ușor de editat. `app.py` le folosește la seed în
#    tabelele lookup și `models.py` validează incidentele față de ele.
# ---------------------------------------------------------------------------

# Tipuri de incident — index.html l.945 (+ mapările de culoare din l.347)
INCIDENT_TYPES = [
    "Crisis",
    "Behavioural",
    "Self-Injury",
    "Elopement",
    "Property Destruction",
    "Other",
]

# Niveluri de severitate — index.html (clasele sev-btn high/medium/low)
SEVERITY_LEVELS = ["High", "Medium", "Low"]

# Antecedente / declanșatoare — extrase din câmpul `trigger` al incidentelor
TRIGGERS = [
    "Transition",
    "Noise",
    "Demand",
    "Sensory",
    "Peer Interaction",
    "Schedule Change",
    "Unknown",
]

# Intervenții — extrase din array-urile `interventions` ale incidentelor
INTERVENTIONS = [
    "Calm Space",
    "Deep Pressure",
    "Sensory Tool",
    "Verbal Redirection",
    "Weighted Blanket",
    "Physical Support",
    "Choice Board",
    "Social Story",
    "Timer",
]

# Rezultate — extrase din câmpul `outcome` al incidentelor
OUTCOMES = [
    "De-escalated",
    "Resolved",
    "Required Additional Support",
]

# Status incident — extrase din câmpul `status`
STATUSES = ["Active", "Resolved"]

# Niveluri de suport per elev — extrase din câmpul `support` (CHILDREN)
SUPPORT_LEVELS = ["High", "Medium", "Low"]

# ---------------------------------------------------------------------------
# 5a. THERAPY SESSIONS — ad-hoc structured sessions
# ---------------------------------------------------------------------------

THERAPY_SKILL_AREAS = [
    "Receptive Language",
    "Expressive Language",
    "Self-Care",
    "Social Skills",
    "Fine Motor",
    "Gross Motor",
    "Cognitive Skills",
    "Communication",
]

PROMPT_LEVELS = [
    "Independent",
    "Gestural",
    "Verbal",
    "Physical",
    "Full Physical",
]

GOAL_STATUSES = ["Active", "Achieved", "Paused", "Discontinued"]

SESSION_STATUSES = ["Planned", "Completed", "Cancelled"]

# ---------------------------------------------------------------------------
# 5b. SEIZURE / EPILEPSY LOG
# ---------------------------------------------------------------------------

SEIZURE_TYPES = [
    "Tonic-Clonic",
    "Absence",
    "Focal",
    "Atonic",
    "Myoclonic",
    "Unknown",
]

SEIZURE_POSITIONS = [
    "Standing",
    "Seated",
    "Floor",
    "Lying",
    "Unknown",
]

# ---------------------------------------------------------------------------
# 5. SETĂRI FLASK / BAZĂ DE DATE
# ---------------------------------------------------------------------------
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def app_data_dir():
    """Dir scriibil pentru DB: lângă .exe când e frozen, altfel rădăcina proiectului."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return BASE_DIR


INSTANCE_DIR = os.path.join(app_data_dir(), "instance")

SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "behaviour.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Schimbă în producție / la împachetarea .exe
SECRET_KEY = os.environ.get("EDIAI_SECRET_KEY", "dev-change-me")

# Dacă True, `app.py` populează baza de date goală cu un set demonstrativ
# minim de elevi/incidente (NU datele reale din mockup) la prima rulare.
SEED_DEMO_DATA = not getattr(sys, "frozen", False)   # blank slate în build-ul .exe

# Elevi generici de demonstrație (NU nume reale). Folosiți doar dacă
# SEED_DEMO_DATA este True. keyWorker referă un nume din STAFF.
DEMO_CHILDREN = [
    {"name": "Student A", "room": "Room 1", "age": 8, "support": "High", "keyWorker": "Staff Member 1"},
    {"name": "Student B", "room": "Room 2", "age": 9, "support": "Medium", "keyWorker": "Staff Member 2"},
    {"name": "Student C", "room": "Room 3", "age": 10, "support": "Low", "keyWorker": "Staff Member 3"},
    {"name": "Student D", "room": "Room 4", "age": 11, "support": "High", "keyWorker": "Staff Member 4"},
]
