# PyInstaller Packaging (.exe) — Design Spec

**Date:** 2026-06-11
**Status:** Approved (pending spec review)

## Problem

The app runs only from a Python venv (`run_app.bat`). A school's non-technical user needs a
single distributable Windows executable that launches the app with no Python install.

## Goal

Produce a one-file Windows `.exe` (console) that, when double-clicked, starts the Flask server,
opens the browser, and stores its SQLite database next to the executable so data persists across
runs. Packaged builds start as a blank slate (no demo students/incidents).

## Non-Goals

- Code signing / installer (MSI) — the raw `.exe` is enough for v1.
- Cross-platform builds (Windows only).
- Auto-update, service install, or a system-tray app.
- Changing the port (fixed at 5000 for v1).

## Decisions (locked)

- **one-file** `.exe`; **console** window; **auto-open** browser; **blank slate** when frozen.

## Architecture

### Frozen-aware data path (`config.py`)

When frozen by PyInstaller (`getattr(sys, "frozen", False)`), `sys.executable` is the `.exe` and
`__file__`/`BASE_DIR` points into the volatile one-file temp dir. The database must live next to
the `.exe`:

```python
import sys
def app_data_dir():
    """Writable dir for the DB: next to the .exe when frozen, else the project root."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return BASE_DIR

INSTANCE_DIR = os.path.join(app_data_dir(), "instance")
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "behaviour.db")
```

And demo data off for distribution:
```python
SEED_DEMO_DATA = not getattr(sys, "frozen", False)   # blank slate in the packaged build
```
(`create_app()` already calls `os.makedirs(config.INSTANCE_DIR, exist_ok=True)`, so the folder is
created next to the `.exe` on first run.)

### Template resolution (`app.py`)

`Flask(__name__)` resolves `templates/` relative to `app.py`, which is inside the one-file temp
dir when frozen. Resolve it from the bundled resource base explicitly:

```python
import sys
def _resource_base():
    """Read-only resource root: PyInstaller's _MEIPASS when frozen, else this file's dir."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

# in create_app():
app = Flask(__name__, template_folder=os.path.join(_resource_base(), "templates"))
```
There is no `static/` dir, so templates are the only bundled resource. The rest of `create_app`
is unchanged.

### Launcher entry point (`launcher.py`, new)

A dedicated entry the `.exe` runs — the dev `app.run(debug=True)` reloader cannot run frozen.

```python
"""launcher.py — entry-point pentru build-ul .exe (fără reloader)."""
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
`app.py`'s existing `if __name__ == "__main__": app.run(debug=True)` stays for development.

### PyInstaller spec (`ediai.spec`, new)

One-file, console, entry `launcher.py`. Bundles `templates/` and collects reportlab's data
(fonts). The settings/reports blueprints are imported lazily inside `create_app`, so they are
declared as hidden imports defensively.

```python
# ediai.spec
from PyInstaller.utils.hooks import collect_all

rl_datas, rl_binaries, rl_hidden = collect_all("reportlab")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=rl_binaries,
    datas=[("templates", "templates")] + rl_datas,
    hiddenimports=["settings_api", "reports_api", "reports", "serializers",
                   "models", "config"] + rl_hidden,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="EDIAIBehaviourTracker",
    debug=False, strip=False, upx=True, console=True,
    disable_windowed_traceback=False,
)
```

### Build script (`build_exe.bat`, new)

```bat
@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\activate.bat" (
    echo [EROARE] venv lipseste. Ruleaza: python -m venv venv ^&^& venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
    pause & exit /b 1
)
call venv\Scripts\activate.bat
python -m pip install -r requirements-dev.txt
pyinstaller ediai.spec --clean --noconfirm
echo.
echo Build gata: dist\EDIAIBehaviourTracker.exe
pause
```

### Misc

- `requirements-dev.txt`: add `pyinstaller>=6.0` (build-time only; not a runtime dependency).
- `.gitignore`: add `build/` and `dist/` (PyInstaller outputs).
- `DEVELOPER_NOTES.md`: tick the PyInstaller item.

## Testing

Unit tests (`tests/test_packaging.py`, new) — the frozen-aware helpers, the only pure logic:
1. `test_app_data_dir_dev` — without `sys.frozen`, `config.app_data_dir()` returns `config.BASE_DIR`.
2. `test_app_data_dir_frozen` — with `monkeypatch.setattr(sys, "frozen", True, raising=False)` and
   a patched `sys.executable`, `app_data_dir()` returns the executable's directory.
3. `test_resource_base_dev` — without frozen, `app._resource_base()` is `app.py`'s directory.
4. `test_resource_base_frozen` — with `sys.frozen` set and `sys._MEIPASS` patched,
   `_resource_base()` returns `_MEIPASS`.

The existing suite must stay green (the path refactor is behavior-preserving in dev).

The actual build + run is **manual verification** (PyInstaller output cannot be exercised by pytest):
- Run `build_exe.bat` → `dist\EDIAIBehaviourTracker.exe` is produced.
- Double-click it: a console appears, the browser opens to the dashboard.
- The app is a blank slate (no demo students); Settings shows seeded Rooms/Staff.
- Log an incident, generate a child PDF — it downloads.
- An `instance\behaviour.db` appears next to the `.exe`; close and relaunch → data persists.
- If PyInstaller misses a hidden import or reportlab font on first run, fix it in `ediai.spec`
  and rebuild (expected iteration).

## Done Criteria

- `python -m pytest -q` green (existing suite + the new path-helper tests; dev behavior unchanged).
- `build_exe.bat` produces `dist\EDIAIBehaviourTracker.exe`.
- Double-clicking the `.exe` launches the server, opens the browser, serves the dashboard, and
  persists `instance\behaviour.db` next to the `.exe` across runs.
- The packaged build starts blank (no demo students/incidents); dev runs keep demo data.
