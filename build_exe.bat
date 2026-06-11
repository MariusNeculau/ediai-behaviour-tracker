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
