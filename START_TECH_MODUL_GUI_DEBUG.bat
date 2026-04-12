@echo off
cd /d C:\PythonProject\TECH_modul
echo [TECH_modul DEBUG] Start z widoczna konsola...
.\.venv\Scripts\python.exe -u C:\PythonProject\TECH_modul\src\app\main.py --no-login
echo.
echo [TECH_modul DEBUG] Zakonczono. Nacisnij dowolny klawisz...
pause >nul
