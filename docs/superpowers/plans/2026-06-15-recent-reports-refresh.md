# Recent Reports Auto-Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tabelul „Recent Reports" reflectă fișierele reale din `Rapoarte_Salvate/` și se actualizează automat după fiecare generare/export reușit.

**Architecture:** `report_storage.list_saved_reports()` listează folderul (newest-first); endpoint nou `GET /api/reports/saved` îl expune; frontend-ul îl încarcă la deschiderea tab-ului Reports și îl reapelează după succesul fetch-urilor de generare.

**Tech Stack:** Python 3, Flask, pytest, JavaScript (vanilla fetch).

---

### Task 1: `report_storage.list_saved_reports()`

**Files:**
- Modify: `report_storage.py`
- Test: `tests/test_report_storage.py`

- [ ] **Step 1: Write the failing tests**

Adaugă în `tests/test_report_storage.py`:

```python
def test_list_saved_reports_empty_when_no_folder(monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path / "nope"))
    import report_storage
    assert report_storage.list_saved_reports() == []


def test_list_saved_reports_newest_first(monkeypatch, tmp_path):
    import os, time
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path))
    import report_storage

    report_storage.save_report("old.pdf", b"%PDF-old")
    time.sleep(0.01)
    report_storage.save_report("new.csv", b"new")
    # asigură mtime distinct/ordonat
    folder = report_storage.reports_dir()
    os.utime(os.path.join(folder, "old.pdf"), (1000, 1000))
    os.utime(os.path.join(folder, "new.csv"), (2000, 2000))

    out = report_storage.list_saved_reports()
    assert [e["filename"] for e in out] == ["new.csv", "old.pdf"]
    assert all(e["generated"] for e in out)        # string nevid
    assert all("_mtime" not in e for e in out)      # câmp intern eliminat
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_report_storage.py -q`
Expected: FAIL — `AttributeError: module 'report_storage' has no attribute 'list_saved_reports'`.

- [ ] **Step 3: Implement `list_saved_reports`**

În `report_storage.py`, schimbă importul de sus din `import os` în:

```python
import os
from datetime import datetime
```

Adaugă la finalul fișierului:

```python
def list_saved_reports():
    """Fișierele din Rapoarte_Salvate/, cele mai noi primele.

    Întoarce [{"filename": str, "generated": "dd Mon yyyy HH:MM"}], sortate
    descrescător după data modificării. [] dacă folderul nu există.
    """
    folder = reports_dir()
    if not os.path.isdir(folder):
        return []
    entries = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        mtime = os.path.getmtime(path)
        entries.append({
            "filename": name,
            "generated": datetime.fromtimestamp(mtime).strftime("%d %b %Y %H:%M"),
            "_mtime": mtime,
        })
    entries.sort(key=lambda e: e["_mtime"], reverse=True)
    for e in entries:
        del e["_mtime"]
    return entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_report_storage.py -q`
Expected: PASS (toate testele din fișier verzi).

- [ ] **Step 5: Commit**

```bash
git add report_storage.py tests/test_report_storage.py
git commit -m "feat: report_storage.list_saved_reports (newest-first folder listing)"
```

---

### Task 2: Endpoint `GET /api/reports/saved`

**Files:**
- Modify: `reports_api.py:18` (import) și adaugă ruta
- Test: `tests/test_reports.py`

- [ ] **Step 1: Write the failing tests**

Adaugă în `tests/test_reports.py`:

```python
def test_list_saved_reports_empty(client, saved_reports_dir):
    res = client.get("/api/reports/saved")
    assert res.status_code == 200
    assert res.get_json() == {"reports": []}


def test_list_saved_reports_after_generate(client, saved_reports_dir):
    gen = client.get("/api/reports/school?period=month")
    saved_name = gen.get_json()["filename"]

    res = client.get("/api/reports/saved")
    assert res.status_code == 200
    names = [r["filename"] for r in res.get_json()["reports"]]
    assert saved_name in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_reports.py -q -k saved`
Expected: FAIL — ruta `/api/reports/saved` nu există (404), deci `get_json()` nu are forma așteptată.

- [ ] **Step 3: Update import in `reports_api.py`**

Schimbă linia de import (în prezent `from report_storage import save_report, FOLDER_NAME`) în:

```python
from report_storage import save_report, list_saved_reports, FOLDER_NAME
```

- [ ] **Step 4: Add the route**

În `reports_api.py`, imediat după definiția `reports_bp = Blueprint(...)` (înainte de `_window_bounds`), adaugă:

```python
@reports_bp.route("/reports/saved", methods=["GET"])
def list_reports():
    return jsonify({"reports": list_saved_reports()})
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_reports.py -q -k saved`
Expected: PASS (2 passed).

- [ ] **Step 6: Run full suite + repo pollution check**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: toate verzi.
Run: `test -d Rapoarte_Salvate && echo POLLUTED || echo CLEAN`
Expected: `CLEAN`.

- [ ] **Step 7: Commit**

```bash
git add reports_api.py tests/test_reports.py
git commit -m "feat: GET /api/reports/saved lists saved report files"
```

---

### Task 3: Frontend — încărcare + auto-refresh „Recent Reports"

**Files:**
- Modify: `templates/dashboard.html` (`renderReports`, `showTab`, `generateReport`, `exportIncidentsCsv`, + `loadRecentReports`/`reportKind`)

- [ ] **Step 1: Replace the hardcoded table source in `renderReports`**

În `renderReports()` (liniile ~767–775), înlocuiește:

```javascript
  // Blank slate: niciun raport generat încă.
  const recentReports=[];
  const reportRows=recentReports.map(r=>`<tr>
    <td><strong style="font-size:13px">${r.name}</strong></td>
    <td><span class="badge badge-resolved">${r.type}</span></td>
    <td style="font-size:13px">${r.child}</td>
    <td style="font-size:13px;color:var(--gray-500)">${r.date}</td>
    <td><button class="dl-btn" onclick="showToast('Raport salvat local: ${r.name}')">&#8681;</button></td>
  </tr>`).join('');
```

cu:

```javascript
  // Lista reală e încărcată asincron de loadRecentReports() din /api/reports/saved.
```

- [ ] **Step 2: Update the table header + tbody in `renderReports`**

În blocul `return` al `renderReports()` (zona „recent-reports", liniile ~815–823), înlocuiește:

```html
  <div class="recent-reports">
    <div class="card-header" style="padding:14px 18px"><div class="card-title">Recent Reports</div></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>File</th><th>Type</th><th>Subject</th><th>Generated</th><th></th></tr></thead>
        <tbody>${reportRows||'<tr><td colspan="5" style="padding:16px;color:var(--gray-500);text-align:center">No reports generated yet</td></tr>'}</tbody>
      </table>
    </div>
  </div>
```

cu:

```html
  <div class="recent-reports">
    <div class="card-header" style="padding:14px 18px"><div class="card-title">Recent Reports</div></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>File</th><th>Type</th><th>Generated</th><th></th></tr></thead>
        <tbody id="recent-reports-body"><tr><td colspan="4" style="padding:16px;color:var(--gray-500);text-align:center">Loading…</td></tr></tbody>
      </table>
    </div>
  </div>
```

- [ ] **Step 3: Add `reportKind` + `loadRecentReports`**

Imediat înainte de `async function generateReport(){` adaugă:

```javascript
function reportKind(fn){
  if(fn.indexOf('Whole_School')!==-1) return 'Whole School';
  if(fn.indexOf('Report_Class')!==-1) return 'Class';
  if(fn.indexOf('Incidents')!==-1) return 'CSV';
  if(fn.indexOf('Report_')!==-1) return 'Child';
  return '—';
}
async function loadRecentReports(){
  const body=document.getElementById('recent-reports-body');
  if(!body) return;
  try{
    const res=await fetch('/api/reports/saved');
    const d=await res.json().catch(()=>({}));
    const list=(d&&d.reports)||[];
    if(!list.length){
      body.innerHTML='<tr><td colspan="4" style="padding:16px;color:var(--gray-500);text-align:center">No reports generated yet</td></tr>';
      return;
    }
    body.innerHTML=list.map(r=>`<tr>
      <td><strong style="font-size:13px">${r.filename}</strong></td>
      <td><span class="badge badge-resolved">${reportKind(r.filename)}</span></td>
      <td style="font-size:13px;color:var(--gray-500)">${r.generated}</td>
      <td><button class="dl-btn" onclick="showToast('Raport salvat local: ${r.filename}')">&#8681;</button></td>
    </tr>`).join('');
  }catch(err){
    body.innerHTML='<tr><td colspan="4" style="padding:16px;color:var(--crisis);text-align:center">Eroare la încărcarea listei.</td></tr>';
  }
}
```

- [ ] **Step 4: Load the list when the Reports tab opens**

În `showTab()` (linia ~388), înlocuiește:

```javascript
  else if(tab==='reports') c.innerHTML=renderReports();
```

cu:

```javascript
  else if(tab==='reports') {c.innerHTML=renderReports(); loadRecentReports();}
```

- [ ] **Step 5: Refresh after a successful report generation**

În `generateReport()`, în ramura de succes, după linia
`showToast('Raportul a fost salvat local în folderul Rapoarte_Salvate');` adaugă pe linie nouă:

```javascript
    loadRecentReports();
```

- [ ] **Step 6: Refresh after a successful CSV export**

În `exportIncidentsCsv()`, după linia
`showToast('Exportul CSV a fost salvat local în folderul Rapoarte_Salvate');` adaugă pe linie nouă:

```javascript
    loadRecentReports();
```

- [ ] **Step 7: Verify no leftover references to the old hardcoded list**

Run: `grep -nE "recentReports|reportRows|<th>Subject</th>" templates/dashboard.html`
Expected: niciun rezultat (exit code 1).

- [ ] **Step 8: Run full suite (frontend change shouldn't break tests)**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: toate verzi.

- [ ] **Step 9: Commit**

```bash
git add templates/dashboard.html
git commit -m "feat: Recent Reports table loads from /api/reports/saved and auto-refreshes"
```

---

## Self-Review

- **Spec coverage:**
  - `report_storage.list_saved_reports()` (newest-first, `[]` la folder lipsă) → Task 1 ✓
  - Endpoint `GET /api/reports/saved` → Task 2 ✓
  - `renderReports` fără array hardcodat + tbody cu id → Task 3 Steps 1-2 ✓
  - `loadRecentReports` + `reportKind` + încărcare la deschiderea tab-ului → Task 3 Steps 3-4 ✓
  - Refresh după succes în `generateReport`/`exportIncidentsCsv` → Task 3 Steps 5-6 ✓
  - Coloane File/Type/Generated (Subject eliminat) → Task 3 Step 2 ✓
  - Unit + endpoint tests → Tasks 1, 2 ✓
  - Repo nepoluat de teste → Task 2 Step 6 ✓
- **Placeholder scan:** „Loading…"/„—" sunt elemente UI intenționate, nu placeholdere de plan. Tot codul e complet.
- **Type consistency:** cheile JSON `filename`/`generated` și `{"reports": [...]}` sunt folosite identic în backend (Task 1/2) și frontend (Task 3); `list_saved_reports` și ruta `/api/reports/saved` consecvente peste tot.
