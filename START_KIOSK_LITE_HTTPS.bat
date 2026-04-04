@echo off
setlocal
cd /d C:\PythonProject\TECH_modul

REM Start HTTPS server in a separate window so this launcher can open the kiosk page.
start "TECH_modul HTTPS Server" /min .\.venv\Scripts\python.exe C:\PythonProject\TECH_modul\src\app\main.py --server --https --https-port 8443

REM Give the server a moment to boot, then open the lightweight Android kiosk.
timeout /t 3 /nobreak >nul
start "" "https://127.0.0.1:8443/kiosk-lite"

endlocal
