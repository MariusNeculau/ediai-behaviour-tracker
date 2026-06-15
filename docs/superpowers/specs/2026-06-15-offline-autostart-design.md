# Design: Offline 100% + Auto-deschidere browser

**Date:** 2026-06-15
**Status:** Approved (design), pending spec review

## Context

EDI AI Behaviour Tracker este o aplicație desktop locală (Flask + SQLite) destinată
rulării într-un mediu fără internet garantat (școală, posibil air-gapped). Două
obiective pentru această iterație:

1. La pornirea serverului în mod dezvoltare/normal (`python app.py`, lansat de
   `run_app.bat`), interfața să se deschidă automat în browser — fără ca
   utilizatorul să tasteze manual adresa.
2. Confirmarea că aplicația se randează 100% offline (zero dependențe CDN).

## Constatări din explorare

- **Auto-deschidere:** `launcher.py` (folosit DOAR la build-ul `.exe`) deschide
  deja browserul automat prin `webbrowser` + `threading.Timer(1.5, ...)`. În
  schimb, `app.py` — entry-point-ul folosit la rularea normală prin `run_app.bat`
  (`python app.py` → `app.run(debug=True)`) — NU deschide browserul. Acesta este
  singurul gap real.
- **Resurse CDN:** scanarea tuturor fișierelor HTML din proiect
  (`templates/dashboard.html`, `legacy/index.html`) nu a găsit NICIO referință
  externă: fără `<link href="http...">`, fără `<script src="http...">`, fără
  `url(http...)`, `@font-face`, `@import` sau domenii CDN
  (googleapis/jsdelivr/cloudflare/unpkg/bootstrapcdn/fontawesome). Tot CSS-ul este
  inline într-un singur `<style>`; fonturile folosesc stiva de sistem
  (`-apple-system, Segoe UI, Roboto`); iconițele sunt emoji/text. Nu există folder
  `static/`. **Aplicația este deja 100% offline.**

## Scope

### Task #1 — Auto-deschidere browser (modificare reală)

Adaug deschiderea automată a browserului în `app.py`, în blocul
`if __name__ == "__main__"`.

Detaliu tehnic critic: `app.run(debug=True)` pornește reloader-ul Werkzeug, care
rulează scriptul în DOUĂ procese (un watcher + procesul-server). O deschidere
naivă ar lansa browserul de două ori. Soluție: deschid browserul DOAR în procesul
real de servire, identificat prin `os.environ.get("WERKZEUG_RUN_MAIN") == "true"`.
Astfel se deschide exact o dată, după ce serverul este efectiv pornit.

**Abordare aleasă (Opțiunea A):** modificare locală în `app.py`, fără a atinge
`launcher.py` (care funcționează deja). Oglindește pattern-ul existent din
`launcher.py` (`Timer(1.5, ...)`). Nu se introduce un helper partajat (YAGNI — cele
două entry-point-uri diferă: debug+reloader vs. frozen).

### Task #2 — Zero Internet (doar confirmare)

Niciun cod de modificat. Aplicația nu are resurse externe de descărcat. Această
secțiune documentează faptul că starea „100% offline" este deja îndeplinită și
verificată prin explorare. (Utilizatorul a optat explicit pentru confirmare fără
adăugarea unui test de pază automat.)

## Implementare (Task #1)

În `app.py`:

```python
import threading
import webbrowser

URL = "http://127.0.0.1:5000/"

def _open_browser():
    webbrowser.open(URL)

if __name__ == "__main__":
    # Reloader-ul (debug=True) rulează scriptul în două procese; deschidem
    # browserul doar în procesul de servire, ca să nu apară două tab-uri.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.5, _open_browser).start()
    app.run(debug=True)
```

`os` este deja importat în `app.py`.

## Error handling

`webbrowser.open()` eșuează silențios (returnează `False`) dacă nu există browser
implicit — serverul pornește oricum și adresa rămâne afișată în consolă de către
`run_app.bat`. Nu adăugăm tratare suplimentară: pe Windows, cazul țintă, există
mereu un browser implicit.

## Testing

- **Manual:** `python app.py` (sau `run_app.bat`) → un singur tab de browser se
  deschide pe `http://127.0.0.1:5000/` după ~1.5s; serverul răspunde.
- **Offline:** cu Wi-Fi oprit, pagina se randează complet identic (deja garantat de
  absența resurselor externe).
- Suita de teste existentă (`tests/`) trebuie să rămână verde — modificarea atinge
  doar blocul `__main__`, neexecutat la import.

## Out of scope

- Modificarea `launcher.py` (funcționează deja).
- Crearea folderului `static/` sau mutarea CSS-ului inline.
- Test automat de pază anti-CDN (respins de utilizator pentru această iterație).
