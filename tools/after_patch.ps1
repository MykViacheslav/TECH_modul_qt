$ErrorActionPreference="Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  throw "Brak .venv. Najpierw uruchom: .\tools\setup_venv.ps1"
}

Write-Host "=== PYTHON VERSION ==="
& $Py --version
Write-Host ""

Write-Host "=== PyQt6 CHECK ==="
& $Py -c "from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR; print('PyQt6', PYQT_VERSION_STR, 'Qt', QT_VERSION_STR)"
Write-Host ""

Write-Host "=== TESTS ==="
& $Py -m pytest -q
Write-Host ""

Write-Host "=== RUN APP ==="
& $Py -m src.app.main