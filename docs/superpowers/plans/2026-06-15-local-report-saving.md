# Local Report Saving Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rapoartele PDF și exportul CSV se salvează fizic în `Rapoarte_Salvate/` lângă aplicație și întorc JSON de succes; UI-ul afișează un toast, fără niciun download din browser.

**Architecture:** Modul nou `report_storage.py` (unde + cum se salvează). Cele 4 endpoint-uri din `reports_api.py` apelează `save_report()` și întorc JSON. Frontend-ul (`dashboard.html`) trece de la `window.location` la `fetch()` + `showToast()`. Testele de endpoint sunt actualizate și redirecționate către `tmp_path` printr-o fixture nouă.

**Tech Stack:** Python 3, Flask, ReportLab, pytest, JavaScript (vanilla fetch).

---

### Task 1: Modul `report_storage.py`

**Files:**
- Create: `report_storage.py`
- Test: `tests/test_report_storage.py`

- [ ] **Step 1: Write the failing test**

`tests/test_report_storage.py`:

```python
import os


def test_reports_dir_is_under_app_data_dir(monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path))
    import report_storage

    d = report_storage.reports_dir()
    assert d == os.path.join(str(tmp_path), "Rapoarte_Salvate")


def test_save_report_writes_file_and_returns_path(monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path))
    import report_storage

    path = report_storage.save_report("demo.pdf", b"%PDF-1.4 test")

    assert os.path.isfile(path)
    assert path == os.path.join(str(tmp_path), "Rapoarte_Salvate", "demo.pdf")
    with open(path, "rb") as f:
        assert f.read() == b"%PDF-1.4 test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_report_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report_storage'`.

- [ ] **Step 3: Write minimal implementation**

`report_storage.py`:

```python
"""report_storage.py — unde și cum se salvează rapoartele generate.

Salvează fișierele într-un folder `Rapoarte_Salvate/` lângă aplicație (lângă .exe
când e frozen, altfel rădăcina proiectului), în loc să le trimită ca download.
"""

import os

import config

FOLDER_NAME = "Rapoarte_Salvate"


def reports_dir():
    """Folderul de salvare; lângă .exe când e frozen, altfel rădăcina proiectului."""
    return os.path.join(config.app_data_dir(), FOLDER_NAME)


def save_report(filename, data):
    """Scrie `data` (bytes) în reports_dir()/filename; întoarce calea absolută."""
    folder = reports_dir()
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_report_storage.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add report_storage.py tests/test_report_storage.py
git commit -m "feat: add report_storage (save reports to Rapoarte_Salvate)"
```

---

### Task 2: Fixture `saved_reports_dir` în conftest

**Files:**
- Modify: `tests/conftest.py` (adaugă o fixture la final)

- [ ] **Step 1: Add the fixture**

La finalul `tests/conftest.py` adaugă:

```python
@pytest.fixture
def saved_reports_dir(monkeypatch, tmp_path):
    """Redirecționează salvarea rapoartelor în tmp_path (nu poluează repo-ul)."""
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path))
    return tmp_path / "Rapoarte_Salvate"
```

`pytest` este deja importat în `conftest.py`.

- [ ] **Step 2: Verify it imports cleanly**

Run: `venv/Scripts/python.exe -m pytest tests/ -q --collect-only`
Expected: colectarea reușește fără erori (fixture-ul e disponibil).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add saved_reports_dir fixture redirecting saves to tmp_path"
```

---

### Task 3: Endpoint-uri `reports_api.py` salvează local + JSON

**Files:**
- Modify: `reports_api.py:10` (import-uri), și cele 4 funcții de endpoint
- Test: `tests/test_reports.py`, `tests/test_exports.py`

- [ ] **Step 1: Update endpoint tests to expect JSON + saved file (failing)**

În `tests/test_reports.py`, înlocuiește corpurile testelor de endpoint astfel:

```python
def test_child_report_pdf_download(client, child_id, saved_reports_dir):
    res = client.get(f"/api/reports/child/{child_id}?period=month")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["folder"] == "Rapoarte_Salvate"
    saved = saved_reports_dir / body["filename"]
    assert saved.is_file()
    assert saved.read_bytes().startswith(b"%PDF")


def test_child_report_default_period(client, child_id, saved_reports_dir):
    res = client.get(f"/api/reports/child/{child_id}")
    assert res.status_code == 200
    assert res.get_json()["success"] is True
```

```python
def test_child_report_with_incident_still_pdf(app, client, child_id, saved_reports_dir):
    from models import db, Incident
    from datetime import datetime

    with app.app_context():
        db.session.add(Incident(
            child_id=child_id, occurred_at=datetime.now(),
            type="Behavioural", severity="High", description="x",
        ))
        db.session.commit()

    res = client.get(f"/api/reports/child/{child_id}?period=term")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert (saved_reports_dir / body["filename"]).read_bytes().startswith(b"%PDF")
```

```python
def test_class_report_pdf_download(client, room_id, saved_reports_dir):
    res = client.get(f"/api/reports/class/{room_id}?period=month")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert (saved_reports_dir / body["filename"]).read_bytes().startswith(b"%PDF")
```

```python
def test_school_report_pdf_download(client, saved_reports_dir):
    res = client.get("/api/reports/school?period=term")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert "Whole_School" in body["filename"]
```

> Nota: dacă corpul existent al `test_child_report_with_incident_still_pdf` diferă
> (creează incidentul altfel), păstrează logica de creare a incidentului existentă
> și schimbă doar aserțiile finale la forma JSON de mai sus.

În `tests/test_exports.py`, înlocuiește testele de endpoint:

```python
def test_export_incidents_csv_download(client, saved_reports_dir):
    res = client.get("/api/export/incidents.csv")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["filename"].endswith(".csv")
    assert (saved_reports_dir / body["filename"]).is_file()


def test_export_incidents_csv_includes_row(app, client, child_id, saved_reports_dir):
    from models import db, Incident
    from datetime import datetime

    with app.app_context():
        db.session.add(Incident(
            child_id=child_id, occurred_at=datetime(2026, 6, 10, 9, 30),
            type="Behavioural", severity="High", description="hit out",
        ))
        db.session.commit()

    res = client.get("/api/export/incidents.csv")
    body = res.get_json()
    text = (saved_reports_dir / body["filename"]).read_text(encoding="utf-8")
    assert "Behavioural" in text
```

> Nota: dacă `test_export_incidents_csv_includes_row` existent creează incidentul
> diferit, păstrează acea logică și schimbă doar partea care citește rezultatul —
> din `client.get(...).get_data(as_text=True)` în citirea fișierului salvat de mai sus.

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_reports.py tests/test_exports.py -q`
Expected: FAIL — endpoint-urile încă întorc PDF/CSV cu `Content-Disposition`, nu JSON; `res.get_json()` întoarce `None`.

- [ ] **Step 3: Update `reports_api.py` imports**

Înlocuiește liniile de import de sus:

```python
import re
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request

from models import db, Child, Incident, Room, SystemConfig
from serializers import serialize_system_config
from reports import (
    period_start, build_child_report, build_class_report, build_school_report,
    render_report_pdf,
)
from exports import incidents_to_csv
from report_storage import save_report, FOLDER_NAME
```

(`Response` eliminat din importul flask — nu mai e folosit.)

- [ ] **Step 4: Update `child_report` to save + JSON**

Înlocuiește blocul final al `child_report` (de la `pdf = render_report_pdf(report)`):

```python
    pdf = render_report_pdf(report)

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", child.name).strip("_") or "child"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_Report_{safe_name}_{period}_{stamp}.pdf"
    try:
        save_report(filename, pdf)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})
```

- [ ] **Step 5: Update `class_report` to save + JSON**

Înlocuiește blocul final al `class_report`:

```python
    pdf = render_report_pdf(report)

    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", room.name).strip("_") or "class"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_Report_Class_{safe_name}_{period}_{stamp}.pdf"
    try:
        save_report(filename, pdf)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})
```

- [ ] **Step 6: Update `school_report` to save + JSON**

Înlocuiește blocul final al `school_report`:

```python
    pdf = render_report_pdf(report)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_Report_Whole_School_{period}_{stamp}.pdf"
    try:
        save_report(filename, pdf)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})
```

- [ ] **Step 7: Update `export_incidents_csv` to save + JSON**

Înlocuiește corpul `export_incidents_csv`:

```python
@reports_bp.route("/export/incidents.csv", methods=["GET"])
def export_incidents_csv():
    incidents = Incident.query.order_by(Incident.occurred_at.desc()).all()
    data = ("﻿" + incidents_to_csv(incidents)).encode("utf-8")  # BOM pentru Excel
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EDI_AI_Incidents_{stamp}.csv"
    try:
        save_report(filename, data)
    except OSError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_reports.py tests/test_exports.py -q`
Expected: PASS (toate testele din ambele fișiere verzi).

- [ ] **Step 9: Run full suite + confirm repo not polluted**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: toate verzi.
Run: `test -d Rapoarte_Salvate && echo POLLUTED || echo CLEAN`
Expected: `CLEAN` (testele scriu doar în tmp_path).

- [ ] **Step 10: Commit**

```bash
git add reports_api.py tests/test_reports.py tests/test_exports.py
git commit -m "feat: report/CSV endpoints save to Rapoarte_Salvate and return JSON"
```

---

### Task 4: Frontend — fetch + toast, fără download

**Files:**
- Modify: `templates/dashboard.html` (`generateReport`, `exportIncidentsCsv`, `showReportModal`, dl-btn)

- [ ] **Step 1: Replace `generateReport` and `exportIncidentsCsv`**

În `templates/dashboard.html` înlocuiește funcțiile (liniile ~897–915):

```javascript
async function generateReport(){
  const type=document.getElementById('r-type').value;
  const periodMap={'This Week':'week','This Month':'month','This Term':'term'};
  const period=periodMap[document.getElementById('r-period').value]||'month';
  let url;
  if(type==='Individual Child'){
    const id=document.getElementById('r-child').value;
    if(!id){alert('Please select a child.');return;}
    url='/api/reports/child/'+id+'?period='+period;
  }else if(type==='Class Summary'){
    const rid=document.getElementById('r-class').value;
    if(!rid){alert('Please select a class.');return;}
    url='/api/reports/class/'+rid+'?period='+period;
  }else{
    url='/api/reports/school?period='+period;
  }
  try{
    const res=await fetch(url);
    const d=await res.json().catch(()=>({}));
    if(!res.ok||!d.success){alert('Generare eșuată: '+(d.error||('HTTP '+res.status)));return;}
    showToast('Raportul a fost salvat local în folderul Rapoarte_Salvate');
  }catch(err){alert('Network error: '+err.message);}
}
async function exportIncidentsCsv(){
  try{
    const res=await fetch('/api/export/incidents.csv');
    const d=await res.json().catch(()=>({}));
    if(!res.ok||!d.success){alert('Export eșuat: '+(d.error||('HTTP '+res.status)));return;}
    showToast('Exportul CSV a fost salvat local în folderul Rapoarte_Salvate');
  }catch(err){alert('Network error: '+err.message);}
}
```

- [ ] **Step 2: Update `showReportModal` wording (remove download)**

În `showReportModal` (linia ~1174), înlocuiește blocul `innerHTML`:

```javascript
  overlay.innerHTML=`<div class="modal" style="text-align:center;padding:36px">
    <div style="font-size:48px;margin-bottom:16px">&#128196;</div>
    <div style="font-size:18px;font-weight:700;margin-bottom:8px">Report Generated</div>
    <div style="font-size:14px;color:var(--gray-700);margin-bottom:20px">EDI_AI_Report_${safeName}.pdf</div>
    <div style="background:var(--gray-100);border-radius:8px;padding:12px;font-size:13px;color:var(--gray-700);margin-bottom:22px">Raportul a fost salvat local în folderul Rapoarte_Salvate.</div>
    <div style="display:flex;gap:10px;justify-content:center">
      <button class="btn-outline" onclick="closeOverlay()">Close</button>
    </div>
  </div>`;
```

- [ ] **Step 3: Update dl-btn toast (remove "Downloading")**

La linia ~774, înlocuiește:

```html
    <td><button class="dl-btn" onclick="showToast('Downloading ${r.name}…')">&#8681;</button></td>
```

cu:

```html
    <td><button class="dl-btn" onclick="showToast('Raport salvat local: ${r.name}')">&#8681;</button></td>
```

- [ ] **Step 4: Verify no `window.location` / "Download" / "Downloading" remain in report flows**

Run: `grep -nE "window\.location|Downloading|ready for download|Download PDF" templates/dashboard.html`
Expected: niciun rezultat (exit code 1).

- [ ] **Step 5: Run full suite (frontend change shouldn't break tests)**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: toate verzi.

- [ ] **Step 6: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: frontend uses fetch + toast for local report saving (no download)"
```

---

## Self-Review

- **Spec coverage:**
  - `report_storage.py` (`reports_dir`, `save_report`) → Task 1 ✓
  - Cele 4 endpoint-uri salvează local + JSON + timestamp unic → Task 3 ✓
  - CSV cu BOM, encode utf-8 → Task 3 Step 7 ✓
  - try/except OSError → 500 JSON → Task 3 ✓
  - Frontend fetch + toast „Raportul a fost salvat local..." → Task 4 ✓
  - Cosmetic showReportModal/dl-btn fără „download" → Task 4 ✓
  - Unit `test_report_storage` + fixture `saved_reports_dir` + teste endpoint actualizate → Tasks 1, 2, 3 ✓
  - Repo nepoluat de teste → Task 3 Step 9 ✓
- **Placeholder scan:** niciun placeholder; tot codul e complet. Notele despre „dacă testul existent diferă" indică exact ce să păstrezi/schimbi.
- **Type consistency:** `save_report(filename, data: bytes)`, `FOLDER_NAME="Rapoarte_Salvate"`, cheile JSON `success`/`filename`/`folder` și fixture-ul `saved_reports_dir` sunt folosite consistent în toate task-urile.
