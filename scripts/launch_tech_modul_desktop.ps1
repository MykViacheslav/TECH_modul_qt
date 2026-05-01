param()

$ErrorActionPreference = "Stop"

$mutexName = "Global\TECH_modul_DESKTOP_launcher_single"
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)
if (-not $createdNew) {
  exit 0
}

try {
  $repoRoot = (Get-Item $PSScriptRoot).Parent.FullName

  function Get-ListenerPid {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) { return $conn.OwningProcess }
    return $null
  }

  function Wait-HttpReady {
    param([string]$Url, [int]$Attempts = 30, [int]$DelayMs = 1000)
    for ($i = 0; $i -lt $Attempts; $i++) {
      try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { return $true }
      } catch {}
      Start-Sleep -Milliseconds $DelayMs
    }
    return $false
  }

  function Get-PythonExe {
    param([string]$Root)
    $candidates = @(
      (Join-Path $Root ".venv\Scripts\pythonw.exe"),
      (Join-Path $Root ".venv\Scripts\python.exe"),
      (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\pythonw.exe"),
      (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\pythonw.exe"),
      (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"),
      (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
      "pythonw",
      "python"
    )
    foreach ($candidate in $candidates) {
      try {
        if ($candidate -in @("python", "pythonw")) {
          & $candidate --version > $null 2>&1
          if ($LASTEXITCODE -eq 0) { return $candidate }
        } elseif (Test-Path $candidate) {
          return $candidate
        }
      } catch { continue }
    }
    return $null
  }

  function Test-DesktopRunning {
    $existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
      Where-Object {
        $_.Name -like "python*.exe" -and
        $_.CommandLine -and
        $_.CommandLine -match "src[\\/]+app[\\/]+main\.py(\s|$)"
      } |
      Select-Object -First 1
    return [bool]$existing
  }

  # Block duplicate GUI windows
  if (Test-DesktopRunning) {
    exit 0
  }

  $pythonExe = Get-PythonExe -Root $repoRoot
  if (-not $pythonExe) {
    [System.Windows.Forms.MessageBox]::Show("Nie znaleziono Pythona. Zainstaluj środowisko .venv.", "TECH_modul")
    exit 1
  }

  # --- Start backend API if not running ---
  $startedBackend = $false
  $backendProc = $null
  $backendPid = Get-ListenerPid -Port 8000

  if (-not $backendPid) {
    $backendLog = Join-Path $repoRoot "backend_desktop.log"
    $backendErrLog = Join-Path $repoRoot "backend_desktop_err.log"

    # Use python.exe (not pythonw) for backend so uvicorn runs properly
    $pythonForBackend = $pythonExe -replace "pythonw\.exe$", "python.exe"
    if (-not (Test-Path $pythonForBackend)) { $pythonForBackend = $pythonExe }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $pythonForBackend
    $psi.Arguments = "-m uvicorn src.api.main_api:app --host 0.0.0.0 --port 8000"
    $psi.WorkingDirectory = $repoRoot
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.EnvironmentVariables["PYTHONPATH"] = $repoRoot

    $backendProc = [System.Diagnostics.Process]::Start($psi)
    $startedBackend = $true

    [void](Wait-HttpReady -Url "http://127.0.0.1:8000/system/summary" -Attempts 30 -DelayMs 1000)
  }

  # --- Start PyQt desktop app ---
  Set-Location $repoRoot
  $guiProc = Start-Process -FilePath $pythonExe `
    -ArgumentList "src/app/main.py" `
    -WorkingDirectory $repoRoot `
    -PassThru `
    -WindowStyle Hidden

  # Wait for rapid double-click guard
  for ($i = 0; $i -lt 20; $i++) {
    if (Test-DesktopRunning) { break }
    Start-Sleep -Milliseconds 100
  }

  # Wait until GUI process exits, then optionally stop the API
  if ($guiProc) {
    Wait-Process -Id $guiProc.Id -ErrorAction SilentlyContinue
  }

  if ($startedBackend -and $backendProc -and -not $backendProc.HasExited) {
    # Only stop API if no other TECH_modul windows are still running
    $stillRunning = Test-DesktopRunning
    if (-not $stillRunning) {
      try { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
  }
}
finally {
  try { $mutex.ReleaseMutex() } catch {}
  $mutex.Dispose()
}
