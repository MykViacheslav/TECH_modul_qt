@echo off
setlocal

REM USTAW IP KOMPUTERA BIURO (serwer TECH_modul)
set "TARGET_URL=http://127.0.0.1:3000/production/biuro"

REM Single-instance browser app: if already opened, do not open another window
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$u='%TARGET_URL%'; $p=Get-CimInstance Win32_Process -Filter \"name='chrome.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like \"*--app=*\" -and $_.CommandLine -like \"*$u*\" }; if($p){ exit 0 } else { exit 1 }"
if not errorlevel 1 (
  echo [INFO] Okno BIURO juz jest otwarte. Pomijam kolejne uruchomienie.
  goto :eof
)

REM Prefer Chrome, fallback to default browser
set "CHROME_1=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "CHROME_2=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set "CHROME_3=%LocalAppData%\Google\Chrome\Application\chrome.exe"

if exist "%CHROME_1%" (
  start "" "%CHROME_1%" --kiosk --app="%TARGET_URL%"
  goto :eof
)
if exist "%CHROME_2%" (
  start "" "%CHROME_2%" --kiosk --app="%TARGET_URL%"
  goto :eof
)
if exist "%CHROME_3%" (
  start "" "%CHROME_3%" --kiosk --app="%TARGET_URL%"
  goto :eof
)

start "" "%TARGET_URL%"
endlocal
