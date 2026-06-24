# ediai.spec — PyInstaller one-file, console build pentru EDI AI Behaviour Tracker.
from PyInstaller.utils.hooks import collect_all

rl_datas, rl_binaries, rl_hidden = collect_all("reportlab")

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=rl_binaries,
    datas=[("templates", "templates")] + rl_datas,
    hiddenimports=[
        "settings_api", "sessions_api", "reports_api", "reports",
        "serializers", "models", "config", "exports", "report_storage",
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
