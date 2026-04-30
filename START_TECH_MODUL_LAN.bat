@echo off
setlocal ENABLEDELAYEDEXPANSION
title TECH MODUL - BIURO LAN
cd /d "%~dp0"
set "FRONTEND_STARTED=0"

echo ======================================================
echo           TECH MODUL - START SYSTEMU (LAN)
echo ======================================================
echo.

if not exist ".\.venv\Scripts\python.exe" (
  echo [BLAD] Brak .venv\Scripts\python.exe
  echo Uruchom najpierw instalacje srodowiska Python.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [BLAD] npm nie jest dostepny w PATH.
  echo Zainstaluj Node.js i uruchom ponownie.
  pause
  exit /b 1
)

set "BIURO_IP="
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /R /C:"IPv4 Address" /C:"Adres IPv4"') do (
  set "CAND=%%A"
  set "CAND=!CAND: =!"
  if not "!CAND!"=="127.0.0.1" if not "!CAND!"=="" (
    set "BIURO_IP=!CAND!"
  )
)

if "%BIURO_IP%"=="" (
  set "BIURO_IP=192.168.8.160"
)

echo BIURO IP: %BIURO_IP%
echo CNC URL : http://%BIURO_IP%:3000/production/cnc
echo.

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if errorlevel 1 (
  echo [1/3] Start backend - port 8000...
  start "TECH MODUL BACKEND" cmd /k "cd /d %~dp0 && .\.venv\Scripts\python.exe -m uvicorn src.api.main_api:app --host 0.0.0.0 --port 8000 --reload"
) else (
  echo [1/3] Backend juz dziala na porcie 8000 - pomijam kolejny start.
)

netstat -ano | findstr /R /C:":3000 .*LISTENING" >nul
if errorlevel 1 (
  echo [2/3] Start frontend - port 3000, host 0.0.0.0...
  start "TECH MODUL FRONTEND" cmd /k "cd /d %~dp0frontend && set NEXT_PUBLIC_API_URL=http://%BIURO_IP%:8000 && npm run dev -- --hostname 0.0.0.0 --port 3000"
  set "FRONTEND_STARTED=1"
) else (
  echo [2/3] Frontend juz dziala na porcie 3000 - pomijam kolejny start.
)

if "%FRONTEND_STARTED%"=="1" (
  echo [3/3] Czekam 10s i otwieram web...
  timeout /t 10 /nobreak >nul
  start "" "http://localhost:3000/"
) else (
  echo [3/3] Aplikacja juz otwarta - nie uruchamiam nowego okna.
)

echo.
echo GOTOWE.
echo Na komputerze CNC otworz: http://%BIURO_IP%:3000/production/cnc
echo.
pause
endlocal
