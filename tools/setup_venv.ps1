$ErrorActionPreference="Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

$Py = Join-Path $Root ".venv\Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r requirements.txt

Write-Host ""
Write-Host "OK: venv gotowy. Interpreter: $Py"
Write-Host "Teraz: .\tools\after_patch.ps1"