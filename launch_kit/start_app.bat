@echo off
REM ===================================================================
REM  start_app.bat — EDI AI Behaviour Tracker
REM  Porneste serverul si deschide automat browserul
REM ===================================================================

cd /d "%~dp0.."

REM Verifica mediul virtual
if not exist "venv\Scripts\activate.bat" (
    echo [EROARE] Mediul virtual nu a fost gasit.
    echo.
    echo Ruleaza o data urmatoarele comenzi in acest folder:
    echo     python -m venv venv
    echo     venv\Scripts\python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Activeaza mediul virtual
call "venv\Scripts\activate.bat"

echo.
echo  ================================================
echo   EDI AI Behaviour Tracker — se porneste...
echo  ================================================
echo.
echo  Serverul va fi disponibil la: http://127.0.0.1:5000
echo  Apasa CTRL+C pentru a opri serverul.
echo.

REM Deschide browserul dupa 2 secunde (in fundal)
start /B cmd /c "timeout /t 2 /nobreak >nul && start """" ""http://127.0.0.1:5000"""

REM Porneste Flask in prim-plan (arata log-urile)
python app.py

REM Mesaj la inchidere
echo.
echo  Serverul s-a oprit. Apasa o tasta pentru a inchide fereastra...
pause >nul
