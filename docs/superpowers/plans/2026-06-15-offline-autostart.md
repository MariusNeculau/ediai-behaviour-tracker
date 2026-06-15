# Offline + Browser Auto-Open Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La rularea `python app.py` browserul se deschide automat o singură dată pe `http://127.0.0.1:5000/`, iar starea „100% offline" e confirmată.

**Architecture:** Modificare locală în `app.py`: helper `_open_browser` + `threading.Timer(1.5, ...)` pornit doar în procesul de servire al reloader-ului (`WERKZEUG_RUN_MAIN == "true"`). `launcher.py` rămâne neatins. Task #2 (CDN) e doar confirmare — fără cod.

**Tech Stack:** Python 3, Flask, Werkzeug reloader, `webbrowser`, `threading`, pytest.

---

### Task 1: Auto-deschidere browser în app.py

**Files:**
- Modify: `app.py` (import-uri sus + bloc `if __name__ == "__main__"` la final)
- Test: `tests/test_autostart.py` (Create)

- [ ] **Step 1: Write the failing test**

`tests/test_autostart.py`:

```python
def test_open_browser_calls_webbrowser_with_local_url(monkeypatch):
    import app as app_module

    opened = {}
    monkeypatch.setattr(app_module.webbrowser, "open", lambda url: opened.setdefault("url", url))

    app_module._open_browser()

    assert opened["url"] == "http://127.0.0.1:5000/"


def test_url_is_loopback_only():
    import app as app_module

    assert app_module.URL == "http://127.0.0.1:5000/"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_autostart.py -v`
Expected: FAIL — `AttributeError: module 'app' has no attribute 'webbrowser'` (și `_open_browser` / `URL` inexistente).

- [ ] **Step 3: Write minimal implementation**

În `app.py`, adaugă la import-uri (lângă `import os`, `import sys`):

```python
import threading
import webbrowser
```

Apoi adaugă, înainte de blocul `if __name__ == "__main__"`:

```python
URL = "http://127.0.0.1:5000/"


def _open_browser():
    webbrowser.open(URL)
```

Și înlocuiește blocul final:

```python
if __name__ == "__main__":
    app.run(debug=True)
```

cu:

```python
if __name__ == "__main__":
    # debug=True pornește reloader-ul Werkzeug, care rulează scriptul în două
    # procese; deschidem browserul doar în procesul de servire ca să nu apară
    # două tab-uri.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.5, _open_browser).start()
    app.run(debug=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_autostart.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run full suite (no regressions)**

Run: `python -m pytest -q`
Expected: toate testele verzi.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_autostart.py
git commit -m "feat: auto-open browser on app.py startup (single tab, reloader-safe)"
```

---

### Task 2: Confirmare Zero-Internet (doar verificare)

**Files:** niciunul (confirmare).

- [ ] **Step 1: Re-confirmă absența resurselor externe**

Run: `grep -rEi "https?://|<link[^>]*href|<script[^>]*src|url\(|@font-face|@import|cdn" templates/`
Expected: niciun rezultat (exit code 1). Confirmă că template-urile nu au dependențe externe.

Niciun commit — nu se modifică fișiere.

---

## Self-Review

- **Spec coverage:** Task #1 (auto-open cu gardă reloader) ✓; Task #2 (confirmare, fără cod/test) ✓.
- **Placeholders:** niciunul — tot codul e complet.
- **Type consistency:** `URL`, `_open_browser`, `webbrowser` folosite consistent între test și implementare.
