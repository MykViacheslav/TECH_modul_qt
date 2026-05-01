param()

$ErrorActionPreference = "Stop"

$mutexName = "Global\TECH_modul_WEB_launcher_single"
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)
if (-not $createdNew) {
  exit 0
}

try {
  $repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
  $frontendCwd = Join-Path $repoRoot "frontend"
  $backendLog    = Join-Path $repoRoot "backend_web.log"
  $backendErrLog = Join-Path $repoRoot "backend_web_err.log"
  $frontendLog   = Join-Path $repoRoot "frontend_web.log"
  $frontendErrLog = Join-Path $repoRoot "frontend_web_err.log"
  # Open WEB shortcut directly in service-pricing view (Giblab-like flow).
  $appUrl = "http://127.0.0.1:3000/services"

  function Get-ListenerPid {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) { return $conn.OwningProcess }
    return $null
  }

  function Wait-HttpReady {
    param(
      [string]$Url,
      [int]$Attempts = 35,
      [int]$DelayMs = 1000
    )
    for ($i = 0; $i -lt $Attempts; $i++) {
      try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
          return $true
        }
      } catch {
      }
      Start-Sleep -Milliseconds $DelayMs
    }
    return $false
  }

  function Get-PythonExe {
    param([string]$Root)
    $candidates = @(
      (Join-Path $Root ".venv\Scripts\python.exe"),
      (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"),
      (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
      "python"
    )
    foreach ($candidate in $candidates) {
      try {
        if ($candidate -eq "python") {
          & $candidate --version > $null 2>&1
          if ($LASTEXITCODE -eq 0) { return $candidate }
        } elseif (Test-Path $candidate) {
          return $candidate
        }
      } catch {
      }
    }
    return $null
  }

  $startedBackend = $false
  $startedFrontend = $false
  $backendProc = $null
  $frontendProc = $null

  $backendPid = Get-ListenerPid -Port 8000
  if (-not $backendPid) {
    $pythonExe = Get-PythonExe -Root $repoRoot
    if (-not $pythonExe) {
      throw "Nie znaleziono Pythona do uruchomienia backendu."
    }
    $backendProc = Start-Process -FilePath $pythonExe `
      -ArgumentList "-m", "uvicorn", "src.api.main_api:app", "--host", "0.0.0.0", "--port", "8000" `
      -WorkingDirectory $repoRoot `
      -RedirectStandardOutput $backendLog `
      -RedirectStandardError $backendErrLog `
      -PassThru `
      -WindowStyle Hidden
    $startedBackend = $true
    [void](Wait-HttpReady -Url "http://127.0.0.1:8000/system/summary" -Attempts 30 -DelayMs 1000)
  }

  $frontendPid = Get-ListenerPid -Port 3000
  if (-not $frontendPid) {
    $npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
    if (-not $npmCmd) {
      $npmCmd = (Get-Command npm -ErrorAction SilentlyContinue).Source
    }
    if (-not $npmCmd) {
      throw "Nie znaleziono npm (Node.js) do uruchomienia frontendu."
    }

    $frontendProc = Start-Process -FilePath $npmCmd `
      -ArgumentList "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000" `
      -WorkingDirectory $frontendCwd `
      -RedirectStandardOutput $frontendLog `
      -RedirectStandardError $frontendErrLog `
      -PassThru `
      -WindowStyle Hidden
    $startedFrontend = $true
    [void](Wait-HttpReady -Url "http://127.0.0.1:3000/" -Attempts 45 -DelayMs 1000)
  }

  $browserCandidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
  )
  $browserExe = $browserCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
  $browserProc = $null

  if ($browserExe) {
    $userDataDir = Join-Path $env:TEMP "tech_modul_web_app_profile"
    $browserProc = Start-Process -FilePath $browserExe `
      -ArgumentList "--app=$appUrl", "--user-data-dir=$userDataDir" `
      -PassThru `
      -WindowStyle Hidden
  } else {
    Start-Process -FilePath $appUrl
  }

  if ($browserProc) {
    Wait-Process -Id $browserProc.Id
  }

  # Close only processes started by this launcher session.
  if ($startedFrontend -and $frontendProc) {
    try {
      Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    } catch {
    }
  }
  if ($startedBackend -and $backendProc) {
    try {
      Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    } catch {
    }
  }
}
finally {
  try { $mutex.ReleaseMutex() } catch {}
  $mutex.Dispose()
}
