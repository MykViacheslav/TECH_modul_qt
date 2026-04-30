param(
  [switch]$DryRun,
  [switch]$KillConflictingPorts
)

# $ErrorActionPreference = "Stop"

$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$backendCwd = $repoRoot
$frontendCwd = Join-Path $repoRoot "frontend"

# Kompatybilne Join-Path
$venvDir = Join-Path $repoRoot ".venv"
$scriptsDir = Join-Path $venvDir "Scripts"
$pythonExe = Join-Path $scriptsDir "python.exe"

if (-not (Test-Path $pythonExe)) {
  Write-Host "ERROR: python.exe not found at $pythonExe" -ForegroundColor Red
  exit 1
}

$backendLog = Join-Path $repoRoot "backend_web.log"
$frontendLog = Join-Path $repoRoot "frontend_web.log"

function Get-Listener {
  param([int]$Port)
  Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Kill-Port {
  param([int]$Port)
  $listener = Get-Listener -Port $Port
  if ($listener) {
    try {
      Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
      Start-Sleep -Milliseconds 800
    } catch {}
  }
}

Write-Host "TECH_MODUL: Thorough cleanup..."
# Kill all node and python processes that might be holding logs
taskkill /f /im node.exe /t 2>$null
taskkill /f /im python.exe /t 2>$null
Start-Sleep -Seconds 1

# Kill conflicting ports
Kill-Port -Port 8000
Kill-Port -Port 5173
Start-Sleep -Milliseconds 500

# Clear log files
Write-Host "Initializing logs..."
try {
    $null > $backendLog
} catch {
    Write-Host "WARNING: Could not truncate $backendLog - it might be locked." -ForegroundColor Yellow
}

try {
    $null > $frontendLog
} catch {
    Write-Host "WARNING: Could not truncate $frontendLog - it might be locked." -ForegroundColor Yellow
}

# Zabijamy istniejace instancje Chrome dla tech_modul, aby nie otwierac 10 okien
Write-Host "Cleaning existing browser windows..."
taskkill /f /im chrome.exe /fi "WINDOWTITLE eq tech_modul*" 2>$null
taskkill /f /im chrome.exe /fi "WINDOWTITLE eq localhost:5173*" 2>$null


Write-Host "Starting servers in background..."
Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "run_backend.ps1")
Start-Process powershell -ArgumentList "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "run_frontend.ps1")


Write-Host "Waiting for backend readiness (max 60s)..."
$backendReady = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/projects" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {}
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ""

if (-not $backendReady) {
    Write-Host "WARNING: Backend did not respond in time. Check backend_web.log" -ForegroundColor Yellow
}

Write-Host "Waiting for frontend readiness (max 60s)..."
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    if (Get-Listener -Port 5173) {
        $ready = $true
        break
    }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ""

if (-not $ready) {
    Write-Host "WARNING: Frontend did not start in time. Check frontend_web.log" -ForegroundColor Yellow
}

$url = "http://localhost:5173"
Write-Host "Launching application: $url"


$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
)
$chromeFound = $false
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $userDataDir = "$env:TEMP\tech_modul_kiosk"
        Start-Process $path -ArgumentList "--app=$url", "--user-data-dir=$userDataDir"
        $chromeFound = $true
        break
    }
}

if (-not $chromeFound) {
    Start-Process $url
}

Write-Host "`n================================================"
Write-Host "   TECH MODUL SYSTEM STARTED"
Write-Host "================================================"
Write-Host "Logs: $backendLog  /  $frontendLog"

