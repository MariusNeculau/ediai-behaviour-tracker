# Design: Actualizare automată a tabelului „Recent Reports"

**Date:** 2026-06-15
**Status:** Approved (design), pending spec review

## Context

După adăugarea salvării locale a rapoartelor (vezi
`2026-06-15-local-report-saving-design.md`), fișierele PDF/CSV ajung în folderul
`Rapoarte_Salvate/`, dar tabelul „Recent Reports" din tab-ul Reports nu reflectă
niciodată fișierele generate.

## Constatare (sursa actuală a tabelului)

În `templates/dashboard.html`, `renderReports()` populează tabelul dintr-un array
**hardcodat gol**: `const recentReports=[];` (linia ~768). Lista nu vine nici din
folder, nici din baza de date — e un placeholder, deci afișează permanent „No
reports generated yet". Nu există nicio sursă de date din care să se reîmprospăteze.

**Concluzie:** trebuie întâi creată sursa de date (un endpoint care listează
folderul `Rapoarte_Salvate/`), apoi frontend-ul o încarcă la deschiderea tab-ului și
o reapelează după fiecare generare reușită.

## Scope

1. Backend: `report_storage.list_saved_reports()` + endpoint `GET /api/reports/saved`.
2. Frontend: încărcarea asincronă a listei la deschiderea tab-ului Reports și
   reîmprospătarea ei după succesul `generateReport()` / `exportIncidentsCsv()`.

## File Structure

- **Modify:** `report_storage.py` — adaugă `list_saved_reports()`.
- **Modify:** `reports_api.py` — adaugă ruta `GET /api/reports/saved`.
- **Modify:** `templates/dashboard.html` — `renderReports()`, `showTab()`,
  `generateReport()`, `exportIncidentsCsv()`, plus funcția nouă `loadRecentReports()`.
- **Modify:** `tests/test_report_storage.py` — unit pentru `list_saved_reports`.
- **Modify:** `tests/test_reports.py` — test pentru `GET /api/reports/saved`.

## Implementare

### `report_storage.py`

```python
from datetime import datetime

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

### `reports_api.py`

Adaugă import-ul și ruta:

```python
from report_storage import save_report, list_saved_reports, FOLDER_NAME

@reports_bp.route("/reports/saved", methods=["GET"])
def list_reports():
    return jsonify({"reports": list_saved_reports()})
```

### `templates/dashboard.html`

În `renderReports()`:
- Elimină `const recentReports=[];` și blocul `reportRows` derivat din el.
- Schimbă antetul tabelului și `<tbody>`:

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

Funcție nouă (lângă `generateReport`):

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

În `showTab()`:

```javascript
  else if(tab==='reports') {c.innerHTML=renderReports(); loadRecentReports();}
```

În `generateReport()`, în ramura de succes (după `showToast(...)`):

```javascript
    showToast('Raportul a fost salvat local în folderul Rapoarte_Salvate');
    loadRecentReports();
```

În `exportIncidentsCsv()`, în ramura de succes (după `showToast(...)`):

```javascript
    showToast('Exportul CSV a fost salvat local în folderul Rapoarte_Salvate');
    loadRecentReports();
```

## Data flow

Deschizi tab Reports → `loadRecentReports()` → `GET /api/reports/saved` →
`list_saved_reports()` citește folderul → JSON `{reports:[...]}` → se umple
`#recent-reports-body`. Generezi raport → succes → `showToast` →
`loadRecentReports()` reîmprospătează tabelul, reflectând noul fișier (newest-first).

## Error handling

- `list_saved_reports()` întoarce `[]` dacă folderul nu există → tabel „No reports
  generated yet".
- Dacă `fetch('/api/reports/saved')` eșuează, `loadRecentReports()` afișează un rând
  de eroare; restul UI rămâne funcțional.

## Testing

- **Unit** `tests/test_report_storage.py` (`config.app_data_dir`→`tmp_path`):
  - Folder inexistent → `list_saved_reports() == []`.
  - După scrierea a două fișiere cu `mtime` diferit (sau `save_report`), lista are 2
    intrări, cel mai recent primul, fiecare cu `filename` și `generated` (string
    nevid). Subfolderele/directoarele sunt ignorate.
- **Endpoint** `tests/test_reports.py` (fixture `saved_reports_dir`):
  - `GET /api/reports/saved` pe folder gol → `200`, `{"reports": []}`.
  - După `GET /api/reports/school?period=month` (care salvează un fișier), un
    `GET /api/reports/saved` întoarce o listă care conține numele fișierului salvat.
- Frontend JS rămâne netestat (consecvent cu restul proiectului).

## Out of scope

- Ștergerea/redenumirea rapoartelor din UI.
- Deschiderea efectivă a fișierului din tabel (butonul rămâne un toast informativ).
- Persistarea metadatelor de raport în baza de date (sursa rămâne folderul).
- Parsarea „subiectului" din numele fișierului (coloana „Subject" e eliminată).
