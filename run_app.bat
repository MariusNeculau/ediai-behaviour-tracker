@echo off
REM ===================================================================
REM  run_app.bat - porneste serverul Flask EDI AI Behaviour Tracker
REM ===================================================================

REM 1. Muta-te in directorul in care se afla acest script (radacina proiectului)
cd /d "%~dp0"

REM 2. Verifica existenta mediului virtual inainte de a-l activa
if not exist "venv\Scripts\activate.bat" (
    echo [EROARE] Nu am gasit mediul virtual "venv".
    echo.
    echo Creeaza-l si instaleaza dependintele cu:
    echo     python -m venv venv
    echo     venv\Scripts\python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM 3. Activeaza mediul virtual
call "venv\Scripts\activate.bat"

REM 4. Porneste serverul Flask
echo.
echo Pornesc serverul Flask pe http://127.0.0.1:5000
echo (Apasa CTRL+C pentru a opri serverul)
echo.
python app.py

REM 5. Mentine fereastra deschisa pentru a vedea eventualele erori
if errorlevel 1 (
    echo.
    echo [EROARE] Aplicatia s-a oprit cu un cod de eroare ^(vezi mesajul de mai sus^).
)
echo.
echo Serverul s-a oprit. Apasa o tasta pentru a inchide fereastra...
pause >nul
