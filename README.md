# EDI AI — Behaviour Tracker

Behaviour incident tracking, seizure logging, and therapy session management for Irish special education schools.

Built in Ireland, for Irish schools. All data stays on school premises.

[![Download .exe](https://img.shields.io/github/v/release/MariusNeculau/ediai-behaviour-tracker?label=Download%20.exe&style=for-the-badge&logo=windows)](https://github.com/MariusNeculau/ediai-behaviour-tracker/releases/latest)
[![Tests](https://img.shields.io/badge/tests-145%20passing-brightgreen?style=for-the-badge)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)

![EDI AI Behaviour Tracker — dashboard](docs/screenshot.png)

---

## Features

### Behaviour Incidents
- Log any incident in under 60 seconds — type, severity, trigger, interventions, outcome
- Dashboard with real-time timeline and peak-hour bar chart
- Per-child pattern analysis: top triggers, most effective interventions, day/time heatmaps

### Seizure Log
- Dedicated epilepsy module: seizure type, duration, position, protocol compliance, medication, post-ictal notes
- School-wide Seizure Log with colour-coded rows (emergency called / protocol not followed)
- Edit or add seizure details after an incident is saved
- Visual stats in Child Profile: SVG bar chart (type distribution) + protocol compliance ring

### Therapy Sessions
- Supervisors create clinical goals per child (skill area, description, target criteria)
- Therapists record session results: total/correct trials, prompt level, accuracy auto-calculated
- Accuracy trend chart per goal; cancel planned sessions; progress summary on Goals table

### Reports & Exports
- **Individual Child PDF** — incident summary, pattern analysis, therapy progress, seizure history
- **Class Summary PDF** and **Whole School PDF**
- **Emergency Protocol Card** — single-page printable PDF with child details, seizure history, and 7-step first-aid protocol
- **Incidents CSV** and **Seizure Log CSV** — UTF-8 BOM for Excel compatibility

### Settings
- School name and roll number editable from the UI
- Rooms, staff, and students fully managed (soft-delete preserves history)
- All behaviour taxonomies (incident types, triggers, interventions) configurable in `config.py`

### GDPR
All data is stored in a local SQLite database (`instance/behaviour.db`). Nothing is transmitted to external servers. Fully compliant with GDPR and the Irish Data Protection Act 2018.

---

## Download

**[⬇ Download the latest Windows app (.exe)](https://github.com/MariusNeculau/ediai-behaviour-tracker/releases/latest/download/EDIAIBehaviourTracker.exe)**

No Python required. Double-click the `.exe` — the app opens automatically in your browser at `http://127.0.0.1:5000`. Keep the `.exe` in its own folder; data is saved to `instance\behaviour.db` next to it.

> **Windows SmartScreen warning?** Choose *More info → Run anyway*. The build is unsigned.

---

## Development Setup

```bash
git clone https://github.com/MariusNeculau/ediai-behaviour-tracker.git
cd ediai-behaviour-tracker

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python app.py
```

App runs at `http://127.0.0.1:5000`. The browser opens automatically.

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest                                         # full suite (145 tests)
pytest tests/test_seizures.py -v               # seizure module only
pytest tests/test_sessions.py -v               # therapy sessions only
```

### Building the Windows .exe

```bash
pip install -r requirements-dev.txt
build_exe.bat
# Output: dist\EDIAIBehaviourTracker.exe
```

---

## Architecture

| Layer | Technology |
|---|---|
| Backend | Flask 3 + Flask-SQLAlchemy |
| Database | SQLite (`instance/behaviour.db`) |
| Frontend | Jinja2 template + vanilla JS (no framework) |
| Reports | ReportLab (PDF) |
| Packaging | PyInstaller (single-file `.exe`) |

**Key files:**

```
app.py              — Flask entry point, routes, DB init
models.py           — SQLAlchemy models (Child, Incident, SeizureDetail,
                      TherapyGoal, TherapySession, …)
config.py           — school identity + all behaviour taxonomies
serializers.py      — JSON serializers for all models
settings_api.py     — CRUD blueprint: rooms, staff, children, seizure summary
sessions_api.py     — Goals, therapy sessions, seizure log, seizure edit
reports_api.py      — PDF generation, CSV export, emergency card
reports.py          — pure report builders + ReportLab PDF renderers
exports.py          — CSV generation (incidents + seizures)
templates/
  dashboard.html    — entire single-page UI (~2 000 lines)
launch_kit/
  start_app.bat     — one-click launcher for school staff
  Presentation.md   — pitch deck for school leadership
  User_Manual.md    — step-by-step guide for non-technical users
docs/superpowers/
  specs/            — feature specifications
  plans/            — implementation plans (therapy v2, seizure log v2)
```

---

## Contact

Marius Neculau — AI Engineer — Galway, Ireland  
mariusneculau@gmail.com
