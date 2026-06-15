# Design: Salvare locală a rapoartelor (fără download în browser)

**Date:** 2026-06-15
**Status:** Approved (design), pending spec review

## Context

EDI AI Behaviour Tracker generează rapoarte PDF (copil/clasă/școală) și un export
CSV. În prezent endpoint-urile întorc fișierul cu `Content-Disposition: attachment`,
deci browserul declanșează un download. Obiectiv: fișierele să fie scrise fizic
într-un folder `Rapoarte_Salvate/` lângă aplicație, iar UI-ul să afișeze doar o
notificare de succes — fără nicio interacțiune de download.

## Constatare prealabilă (Obiectiv #1 — eroarea 500 în PyInstaller)

Reprodus direct pe `dist\EDIAIBehaviourTracker.exe` (build curent): toate cele trei
rapoarte PDF (`/api/reports/school`, `/api/reports/child/<id>`,
`/api/reports/class/<id>`) și `/api/export/incidents.csv` întorc **HTTP 200** cu
fișiere valide; consola exe-ului nu arată niciun traceback. ReportLab este deja
împachetat corect prin `collect_all("reportlab")` din `ediai.spec`. Generarea PDF
folosește exclusiv fonturile încorporate ReportLab (Helvetica) — nu există logo,
fonturi custom sau CSS care să necesite `resource_path`. **Eroarea 500 nu se
reproduce; Obiectiv #1 este considerat rezolvat/verificat. Acest spec acoperă doar
Obiectiv #2.**

## Scope (Obiectiv #2)

Modificarea celor 4 endpoint-uri de export (3 PDF + 1 CSV) să salveze local și să
întoarcă JSON, plus actualizarea frontend-ului să folosească `fetch()` + toast.

## File Structure

- **Create:** `report_storage.py` — unde se salvează rapoartele + scrierea lor.
  - `reports_dir() -> str`: `os.path.join(config.app_data_dir(), "Rapoarte_Salvate")`.
    Citește `config.app_data_dir()` la fiecare apel (lângă `.exe` când e frozen,
    altfel rădăcina proiectului), ca testele să-l poată monkeypatch-ui.
  - `save_report(filename: str, data: bytes) -> str`: `os.makedirs(reports_dir(),
    exist_ok=True)`, scrie `data` (binar) în `reports_dir()/filename`, întoarce
    calea absolută.
- **Modify:** `reports_api.py` — cele 4 endpoint-uri.
- **Modify:** `templates/dashboard.html` — `generateReport()`, `exportIncidentsCsv()`
  și textul cosmetic din `showReportModal` / butonul dl.
- **Create:** `tests/test_report_storage.py` — unit pentru modulul nou.
- **Modify:** `tests/conftest.py` — fixture `saved_reports_dir` care redirecționează
  salvarea către `tmp_path`.
- **Modify:** `tests/test_reports.py`, `tests/test_exports.py` — testele de endpoint.

## Implementare

### `report_storage.py`

```python
"""report_storage.py — unde și cum se salvează rapoartele generate.

Salvează fișierele într-un folder `Rapoarte_Salvate/` lângă aplicație (lângă .exe
când e frozen, altfel rădăcina proiectului), în loc să le trimită ca download.
"""

import os

import config

FOLDER_NAME = "Rapoarte_Salvate"


def reports_dir():
    """Folderul de salvare; creat lângă .exe când e frozen, altfel în rădăcina proiectului."""
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

### `reports_api.py`

Pattern comun pentru cele 3 endpoint-uri PDF (exemplu child):

```python
from datetime import date, datetime, timedelta
from report_storage import save_report, FOLDER_NAME

# ... după pdf = render_report_pdf(report):
safe_name = re.sub(r"[^A-Za-z0-9]+", "_", child.name).strip("_") or "child"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"EDI_AI_Report_{safe_name}_{period}_{stamp}.pdf"
try:
    save_report(filename, pdf)
except OSError as e:
    return jsonify({"success": False, "error": str(e)}), 500
return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})
```

- Class: `filename = f"EDI_AI_Report_Class_{safe_name}_{period}_{stamp}.pdf"`.
- School: `filename = f"EDI_AI_Report_Whole_School_{period}_{stamp}.pdf"`.
- CSV (`export_incidents_csv`):

```python
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"EDI_AI_Incidents_{stamp}.csv"
data = ("﻿" + incidents_to_csv(incidents)).encode("utf-8")  # BOM pentru Excel
try:
    save_report(filename, data)
except OSError as e:
    return jsonify({"success": False, "error": str(e)}), 500
return jsonify({"success": True, "filename": filename, "folder": FOLDER_NAME})
```

`Response` nu mai este folosit pentru aceste endpoint-uri; import-ul rămâne doar dacă
e folosit altundeva (nu este — se elimină din `from flask import ...`).

### `templates/dashboard.html`

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

Cosmetic (eliminăm orice referire la „download"):
- `showReportModal`: textul „...ready for download." → „Raportul a fost salvat local
  în folderul Rapoarte_Salvate."; butonul „&#8681; Download PDF" → eliminat (rămâne
  doar „Close"). Acest modal este un mockup decorativ (nu apelează un endpoint real),
  dar wording-ul nu mai trebuie să sugereze download.
- dl-btn (lista de rapoarte, linia ~774): toast-ul „Downloading ${r.name}…" →
  „Raport salvat local: ${r.name}".

## Data flow

buton → `fetch` GET → endpoint construiește raportul → `save_report` scrie în
`Rapoarte_Salvate/` → JSON `{success, filename, folder}` → `showToast(...)`.

## Error handling

- Scrierea pe disc e protejată de `try/except OSError` → JSON `{success:false,
  error}` cu 500; frontend-ul afișează un `alert` cu mesajul. Restul logicii
  (404 child/room necunoscut, 400 period invalid) rămâne neschimbată, înaintea
  salvării.

## Testing

- **Unit nou** `tests/test_report_storage.py`:
  - `reports_dir()` se termină cu `Rapoarte_Salvate` și e ancorat în
    `config.app_data_dir()` (monkeypatch `config.app_data_dir` → `tmp_path`).
  - `save_report("x.pdf", b"%PDF-")` creează folderul, scrie fișierul, întoarce o
    cale existentă cu conținutul corect.
- **`tests/conftest.py`** — fixture nou:
  ```python
  @pytest.fixture
  def saved_reports_dir(monkeypatch, tmp_path):
      import config
      monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path))
      return tmp_path / "Rapoarte_Salvate"
  ```
- **Endpoint-uri actualizate** (folosesc fixture-ul `saved_reports_dir` ca să NU
  scrie în rădăcina repo-ului):
  - `test_reports.py`: `test_child_report_pdf_download`,
    `test_child_report_default_period`, `test_child_report_with_incident_still_pdf`,
    `test_class_report_pdf_download`, `test_school_report_pdf_download` →
    aserții noi: `status_code == 200`, `res.is_json`, `res.get_json()["success"]
    is True`, fișierul `.pdf` există în `saved_reports_dir` cu antet `%PDF`.
  - `test_exports.py`: `test_export_incidents_csv_download`,
    `test_export_incidents_csv_includes_row` → JSON `success`, fișierul `.csv`
    există în `saved_reports_dir` și conține rândurile așteptate (citit din fișier,
    nu din răspuns).
  - Testele 404/400 rămân neschimbate (apar înainte de salvare; nu scriu fișiere).
- Testele pure (`build_*`, `render_*`) rămân neschimbate.
- Suita completă trebuie să rămână verde și să NU creeze `Rapoarte_Salvate/` în
  rădăcina repo-ului.

## Out of scope

- Wiring-ul butonului per-copil „Generate Report" (mockup `showReportModal`) la un
  endpoint real — rămâne mockup, doar wording actualizat.
- Modificarea metodei HTTP (rămâne GET, ca să nu rupem testele/consumatorii).
- Orice schimbare la layout-ul PDF sau la conținutul CSV.
