# Developer Notes: EDI AI Behaviour Tracker (Local Desktop)

## Obiectiv
Migrarea aplicației de la un stack Web (Next.js/Firebase) la un stack Local Desktop (Flask/SQLite), generând un sistem "blank slate" complet customizabil.

## Arhitectură
- **Backend:** Flask (Python)
- **Database:** SQLite (local, `instance/behaviour.db`)
- **Frontend:** Jinja2 templates (renderizat de Flask)
- **Config:** `config.py` pentru entități (comportamente, elevi, setări) - FĂRĂ referințe hardcoded.

## Task-uri curente (Migration Roadmap)
1. [x] Analiza fișierelor existente și identificarea referințelor specifice "Saplings Special School" (5 apariții în `index.html`).
2. [x] Ștergerea fișierelor/codului redundant și transformarea în template generic. Mockup-ul a fost arhivat în `legacy/index.html`.
3. [x] Definire modele de date (SQLAlchemy) în `models.py` (`Child`, `Staff`, `Incident`, `Intervention`).
4. [x] Creare `config.py` pentru personalizarea categoriilor (școală, clase, staff, taxonomii).
5. [x] Implementare `app.py` și servire frontend generic. `templates/dashboard.html` portat din `legacy/index.html`: identitate școală + taxonomii injectate din `config.py`, date din SQLite (goale = blank slate). Verificat cu `app.test_client()`: `GET /` → 200, fără referințe "Saplings", fără Jinja neevaluat.
6. [ ] Împachetare cu PyInstaller pentru .exe.

## Task-uri rămase (post-pas 5)
- [x] Persistare formular: `POST /api/incidents` implementat; `saveIncident()` salvează în SQLite. Demo children seed-uite generic.
- Settings CRUD (în lucru, branch `feature/settings-crud`):
  - [x] Fundație schemă: `Room` ca tabel cu FK (`Child.room_id`), flag-uri `active` (soft-delete) pe `Child`/`Staff`, modul `serializers.py`.
  - [x] Rooms API (`/api/rooms` GET/POST/PUT/DELETE) cu soft-delete + blocare 409 la arhivare în uz.
  - [x] Staff API (`/api/staff` GET/POST/PUT/DELETE) cu blocare 409 dacă e key worker activ. Teste verzi (22 passed).
  - [ ] Children API (`/api/children`) — următorul task.
  - [ ] Frontend Settings (tabele + modale Add/Edit/Archive, rooms dinamice).
- Generare reală rapoarte PDF.

## Status:
Backend + frontend generic funcționale local (Flask + SQLite). Rulat și verificat prin test client (`GET /` 200, `GET /api/config` 200). Următorul pas major: pasul 6 (PyInstaller) sau persistarea incidentelor.