@echo off
setlocal

set "REPO=C:\PythonProject\TECH_modul"
set "BIURO_IP=192.168.8.160"
set "LOG=%REPO%\biuro_onlogon.log"
set "TARGET_URL=http://127.0.0.1:3000/production/biuro"

echo.>> "%LOG%"
echo ===============================>> "%LOG%"
echo START %date% %time%>> "%LOG%"
echo REPO=%REPO%>> "%LOG%"
echo BIURO_IP=%BIURO_IP%>> "%LOG%"

cd /d "%REPO%"

REM If app is already running, do not restart or open duplicate windows
set "ALREADY_RUNNING=0"
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if not errorlevel 1 (
  netstat -ano | findstr /R /C:":3000 .*LISTENING" >nul
  if not errorlevel 1 (
    set "ALREADY_RUNNING=1"
  )
)

if "%ALREADY_RUNNING%"=="1" (
  echo App already running - skipping duplicate start>> "%LOG%"
  goto :end
)

REM Free default ports if occupied
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
echo Ports cleaned>> "%LOG%"

REM Clear broken Next cache/chunks to avoid MODULE_NOT_FOUND like ./761.js
if exist "%REPO%\frontend\.next" (
  rmdir /s /q "%REPO%\frontend\.next" >nul 2>&1
  echo Cleared frontend\\.next cache>> "%LOG%"
)
if exist "%REPO%\frontend.log" (
  del /f /q "%REPO%\frontend.log" >nul 2>&1
)

REM Start backend
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','%REPO%\scripts\run_backend.ps1' -WindowStyle Hidden"
echo Backend start command sent>> "%LOG%"

REM Wait until backend API responds (max ~60s)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; 1..30 | ForEach-Object { try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/production/tasks?station=biuro&status=active&limit=1' -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { $ok=$true; break } } catch {}; Start-Sleep -Seconds 2 }; if (-not $ok) { exit 1 }"
if errorlevel 1 (
  echo Backend readiness timeout on http://127.0.0.1:8000>> "%LOG%"
  goto :end
)
echo Backend ready>> "%LOG%"

REM Start frontend (logged to frontend.log by run_frontend.ps1)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:NEXT_PUBLIC_API_URL='http://%BIURO_IP%:8000'; Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','%REPO%\scripts\run_frontend.ps1' -WindowStyle Hidden"
echo Frontend start command sent via run_frontend.ps1>> "%LOG%"

REM Wait until frontend responds (max ~120s)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; 1..60 | ForEach-Object { try { $r=Invoke-WebRequest -UseBasicParsing -Uri '%TARGET_URL%' -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { $ok=$true; break } } catch {}; Start-Sleep -Seconds 2 }; if (-not $ok) { exit 1 }"
if errorlevel 1 (
  echo Frontend readiness timeout for %TARGET_URL%>> "%LOG%"
  goto :end
)

REM Open BIURO terminal kiosk
call "%REPO%\BIURO_AUTOSTART.bat"
echo Browser open command sent>> "%LOG%"
echo END OK %date% %time%>> "%LOG%"

:end

endlocal
