@echo on
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

:: --- KROK 1: BACKEND (port 8000) ---
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if errorlevel 1 (
  echo Backend starting...
) else (
  echo Backend already running
)

:: --- KROK 2: FRONTEND (port 5173) ---
netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul
if errorlevel 1 (
  echo Frontend starting...
) else (
  echo Frontend already running
)

pause
