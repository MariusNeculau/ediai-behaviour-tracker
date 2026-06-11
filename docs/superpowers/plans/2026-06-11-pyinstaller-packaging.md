# PyInstaller Packaging (.exe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the Flask app as a one-file Windows `.exe` (console) that launches the server, opens the browser, and persists its SQLite DB next to the executable; packaged builds start blank.

**Architecture:** Make `config.py` and `app.py` frozen-aware (DB next to the `.exe`, templates from `sys._MEIPASS`, demo off when frozen). A dedicated `launcher.py` runs the server without the reloader. A committed `ediai.spec` + `build_exe.bat` build the one-file exe. The pure path helpers are unit-tested; the build/run is verified manually.

**Tech Stack:** Python, Flask, PyInstaller, pytest.

---

## File Structure

- `config.py` (modify) — `import sys`; `app_data_dir()`; DB path next to `.exe` when frozen; `SEED_DEMO_DATA` off when frozen.
- `app.py` (modify) — `import sys`; `_resource_base()`; `Flask(..., template_folder=...)`.
- `launcher.py` (create) — frozen entry point (open browser + run server, no reloader).
- `ediai.spec` (create) — PyInstaller one-file console spec.
- `build_exe.bat` (create) — build script.
- `requirements-dev.txt` (modify) — add `pyinstaller`.
- `.gitignore` (modify) — ignore `build/`, `dist/`.
- `tests/test_packaging.py` (create) — unit tests for the frozen-aware helpers.
- `DEVELOPER_NOTES.md` (modify) — tick the PyInstaller item.

---

## Task 1: Confirm baseline

- [ ] **Step 1: Run the suite**

Run: `python -m pytest -q`
Expected: all PASS (57). No DB schema change in this feature.

---

## Task 2: `config.py` — frozen-aware data dir + demo off when frozen

**Files:** Modify `config.py`, create `tests/test_packaging.py`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_packaging.py`:

```python
import os
import sys


def test_app_data_dir_dev(monkeypatch):
    import config
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert config.app_data_dir() == config.BASE_DIR


def test_app_data_dir_frozen(monkeypatch, tmp_path):
    import config
    exe = tmp_path / "EDIAIBehaviourTracker.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)
    assert config.app_data_dir() == str(tmp_path)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_packaging.py -k app_data_dir -v`
Expected: FAIL — `AttributeError` (`config.app_data_dir` does not exist).

- [ ] **Step 3: Edit `config.py`**

In section 5 ("SETĂRI FLASK / BAZĂ DE DATE"), change:
```python
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
```
to:
```python
import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def app_data_dir():
    """Dir scriibil pentru DB: lângă .exe când e frozen, altfel rădăcina proiectului."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return BASE_DIR


INSTANCE_DIR = os.path.join(app_data_dir(), "instance")
```

Then change the demo flag line:
```python
SEED_DEMO_DATA = True
```
to:
```python
SEED_DEMO_DATA = not getattr(sys, "frozen", False)   # blank slate în build-ul .exe
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_packaging.py -k app_data_dir -v`
Expected: both PASS. Then `python -m pytest -q` → all green (dev behavior unchanged; `INSTANCE_DIR` still resolves to `BASE_DIR/instance` in dev).

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_packaging.py
git commit -m "feat: frozen-aware data dir + blank slate when packaged"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 3: `app.py` — resolve templates from the bundled resource base

**Files:** Modify `app.py`, `tests/test_packaging.py`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_packaging.py`:

```python
def test_resource_base_dev(monkeypatch):
    import app
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert app._resource_base() == os.path.dirname(os.path.abspath(app.__file__))


def test_resource_base_frozen(monkeypatch, tmp_path):
    import app
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert app._resource_base() == str(tmp_path)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_packaging.py -k resource_base -v`
Expected: FAIL — `AttributeError` (`app._resource_base` does not exist).

- [ ] **Step 3: Edit `app.py` imports**

Change the import line:
```python
import os
from datetime import date, datetime
```
to:
```python
import os
import sys
from datetime import date, datetime
```

- [ ] **Step 4: Add `_resource_base()` and use it for the template folder**

Directly ABOVE `def create_app():`, add:
```python
def _resource_base():
    """Rădăcina resurselor read-only: sys._MEIPASS când e frozen, altfel dir-ul acestui fișier."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


```

Then in `create_app()`, change:
```python
    app = Flask(__name__)
```
to:
```python
    app = Flask(__name__, template_folder=os.path.join(_resource_base(), "templates"))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_packaging.py -k resource_base -v`
Expected: both PASS. Then `python -m pytest -q` → all green (the dashboard still renders: in dev `_resource_base()` is `app.py`'s dir, so `templates/` resolves as before).

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_packaging.py
git commit -m "feat: resolve Flask templates from bundled resource base (frozen-aware)"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 4: `launcher.py` — frozen entry point

**Files:** Create `launcher.py`.

- [ ] **Step 1: Create `launcher.py`**

```python
"""launcher.py — entry-point pentru build-ul .exe.

Pornește serverul Flask FĂRĂ reloader (reloader-ul nu funcționează frozen) și
deschide automat browserul. În dezvoltare folosește în continuare `python app.py`.
"""

import threading
import webbrowser

from app import app

URL = "http://127.0.0.1:5000/"


def _open_browser():
    webbrowser.open(URL)


if __name__ == "__main__":
    threading.Timer(1.5, _open_browser).start()
    print(f"EDI AI Behaviour Tracker running at {URL}  (close this window to stop)")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
```

- [ ] **Step 2: Smoke-test that the launcher imports cleanly**

Run: `python -c "import launcher; print('ok', launcher.URL)"`
Expected: prints `ok http://127.0.0.1:5000/` (importing must not start the server — it only runs under `__main__`).

- [ ] **Step 3: Commit**

```bash
git add launcher.py
git commit -m "feat: add launcher entry point for the packaged app"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 5: PyInstaller spec, build script, dev deps, gitignore

**Files:** Create `ediai.spec`, `build_exe.bat`; modify `requirements-dev.txt`, `.gitignore`.

- [ ] **Step 1: Create `ediai.spec`**

```python
# ediai.spec — PyInstaller one-file, console build pentru EDI AI Behaviour Tracker.
from PyInstaller.utils.hooks import collect_all

rl_datas, rl_binaries, rl_hidden = collect_all("reportlab")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=rl_binaries,
    datas=[("templates", "templates")] + rl_datas,
    hiddenimports=[
        "settings_api", "reports_api", "reports", "serializers",
        "models", "config",
    ] + rl_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EDIAIBehaviourTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

- [ ] **Step 2: Create `build_exe.bat`**

```bat
@echo off
REM build_exe.bat - construieste dist\EDIAIBehaviourTracker.exe cu PyInstaller.
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [EROARE] Nu am gasit "venv".
    echo Creeaza-l: python -m venv venv ^&^& venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m pip install -r requirements-dev.txt
pyinstaller ediai.spec --clean --noconfirm
echo.
echo Build gata: dist\EDIAIBehaviourTracker.exe
pause
```

- [ ] **Step 3: Add PyInstaller to `requirements-dev.txt`**

Append this line to `requirements-dev.txt`:
```
pyinstaller>=6.0
```

- [ ] **Step 4: Ignore build outputs in `.gitignore`**

Append these lines to `.gitignore`:
```
# PyInstaller build outputs
build/
dist/
```

- [ ] **Step 5: Sanity-check the spec parses as Python**

Run: `python -c "compile(open('ediai.spec').read(), 'ediai.spec', 'exec'); print('spec OK')"`
Expected: prints `spec OK` (syntax check only — does not execute the build).

- [ ] **Step 6: Commit**

```bash
git add ediai.spec build_exe.bat requirements-dev.txt .gitignore
git commit -m "build: add PyInstaller one-file spec and build script"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Task 6: Manual build + run verification, developer notes

**Files:** Modify `DEVELOPER_NOTES.md`.

- [ ] **Step 1: Build the executable**

Run (PowerShell): `python -m pip install -r requirements-dev.txt` then `pyinstaller ediai.spec --clean --noconfirm`
(Or double-click `build_exe.bat`.)
Expected: build finishes; `dist\EDIAIBehaviourTracker.exe` exists. If PyInstaller reports a
missing module or reportlab font at runtime (next step), add it to `hiddenimports`/`datas` in
`ediai.spec` and rebuild — this iteration is expected.

- [ ] **Step 2: Run the executable from a clean folder**

Copy `dist\EDIAIBehaviourTracker.exe` to an empty folder and double-click it (or run it from a
terminal). Verify, in order:
1. A console window appears printing the running URL, and the browser opens to the dashboard.
2. The app is a **blank slate** — no demo students; Settings → Students is empty, but Settings
   shows seeded Rooms and Staff and a System section.
3. Add a student, log an incident for them, then Reports → Individual Child → Generate → a PDF
   downloads.
4. An `instance\behaviour.db` file appears **next to the .exe** in that folder.
5. Close the console, relaunch the `.exe` → the student/incident from step 3 are still there
   (data persisted).

Expected: all five hold. If not, capture the console error and fix `ediai.spec` (Step 1).

- [ ] **Step 3: Update `DEVELOPER_NOTES.md`**

Find the line:
```
6. [ ] Împachetare cu PyInstaller pentru .exe.
```
Replace with:
```
6. [x] Împachetare cu PyInstaller pentru .exe: `launcher.py` + `ediai.spec` (one-file, consolă, auto-open browser); DB lângă .exe (persistent), blank slate la build. Build: `build_exe.bat` → `dist\EDIAIBehaviourTracker.exe`.
```

- [ ] **Step 4: Commit**

```bash
git add DEVELOPER_NOTES.md
git commit -m "docs: mark PyInstaller packaging done"
```
End the commit message body with:
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

---

## Done criteria

- `python -m pytest -q` green (existing suite + the new path-helper tests; dev behavior unchanged).
- `pyinstaller ediai.spec` (or `build_exe.bat`) produces `dist\EDIAIBehaviourTracker.exe`.
- Running the `.exe` launches the server, opens the browser, serves the dashboard, and persists
  `instance\behaviour.db` next to the `.exe` across runs.
- The packaged build starts blank (no demo students/incidents); `python app.py` in dev keeps demo data.
