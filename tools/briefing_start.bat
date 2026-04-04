@echo off
REM ================================================================
REM  TECH_modul — Codzienny Briefing Deweloperski
REM  Uruchamiaj przez Windows Task Scheduler o 7:00
REM  Uzywa VBS wrappera zeby nie pokazywac okna CMD/PowerShell
REM ================================================================

set PROJECT=C:\PythonProject\TECH_modul
set VBS=%PROJECT%\tools\briefing_hidden.vbs

REM Uruchom przez wscript.exe — brak widocznego okna
if exist "%VBS%" (
    wscript.exe "%VBS%"
    exit /b
)

REM Fallback (jesli brak VBS): stary sposob z oknem
set PYTHON=%PROJECT%\.venv\Scripts\python.exe
set SCRIPT=%PROJECT%\tools\dev_briefing.py
set OUTPUT=%PROJECT%\briefing.txt
cd /d "%PROJECT%"
set PYTHONUTF8=1
"%PYTHON%" "%SCRIPT%"
if exist "%OUTPUT%" (
    start notepad "%OUTPUT%"
)
