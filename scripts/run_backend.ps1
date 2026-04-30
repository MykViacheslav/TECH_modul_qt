$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$venvDir = Join-Path $repoRoot ".venv"
$scriptsDir = Join-Path $venvDir "Scripts"
$venvPython = Join-Path $scriptsDir "python.exe"
$py310 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"
$py311 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
$log = Join-Path $repoRoot "backend_web.log"

$pythonCandidates = @($venvPython, $py310, $py311, "python")
$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
  try {
    if ($candidate -eq "python") {
      & $candidate --version > $null 2>&1
      if ($LASTEXITCODE -eq 0) { $pythonExe = $candidate; break }
    } elseif (Test-Path $candidate) {
      & $candidate --version > $null 2>&1
      if ($LASTEXITCODE -eq 0) { $pythonExe = $candidate; break }
    }
  } catch {}
}

if (-not $pythonExe) {
  "ERROR: No working Python executable found. Checked: $($pythonCandidates -join ', ')" | Out-File -FilePath $log -Encoding utf8
  exit 1
}

Set-Location $repoRoot
& "$pythonExe" -m uvicorn src.api.main_api:app --host 0.0.0.0 --port 8000 --reload > "$log" 2>&1
