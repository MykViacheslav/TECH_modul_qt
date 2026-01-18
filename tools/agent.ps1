param(
  [Parameter(Mandatory=$true)][string]$Title,
  # command to run AFTER step (for example: python patch script)
  [Parameter(Mandatory=$false)][string]$Do = "",
  # run app at end?
  [switch]$Run
)

$ErrorActionPreference="Stop"

$Proj = Split-Path -Parent $PSScriptRoot
$Src  = Join-Path $Proj "src"
$Tools = Join-Path $Proj "tools"
$Handoff = Join-Path $Proj "_handoff"
if(-not (Test-Path $Handoff)){ New-Item -ItemType Directory -Path $Handoff | Out-Null }

$Venv = Join-Path $Proj ".venv"
$Py   = Join-Path $Venv "Scripts\python.exe"
$Pip  = Join-Path $Venv "Scripts\pip.exe"
if(-not (Test-Path $Py)){ python -m venv $Venv }
try { & $Py -c "import PySide6" | Out-Null } catch { & $Pip install PySide6 | Out-Host }

function Fail-And-Undo([string]$msg){
  Write-Host "❌ $msg" -ForegroundColor Red
  if(Test-Path (Join-Path $Tools "undo_last.ps1")){
    Write-Host "↩️  AUTO-UNDO (undo_last.ps1)..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File (Join-Path $Tools "undo_last.ps1") | Out-Host
  } else {
    Write-Host "WARN: tools\undo_last.ps1 not found." -ForegroundColor Yellow
  }
  throw $msg
}

# --- STEP ---
if(Test-Path (Join-Path $Tools "step.ps1")){
  Write-Host "== STEP ==" -ForegroundColor Cyan
  powershell -ExecutionPolicy Bypass -File (Join-Path $Tools "step.ps1") $Title | Out-Host
} else {
  Write-Host "WARN: tools\step.ps1 not found (no snapshot)." -ForegroundColor Yellow
}

# --- DO (optional) ---
if($Do -and $Do.Trim().Length -gt 0){
  Write-Host "== DO ==" -ForegroundColor Cyan
  $log = Join-Path $Handoff ("agent_do_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".txt")
  try {
    cmd /c $Do 2>&1 | Tee-Object -FilePath $log | Out-Host
  } catch {
    Get-Content $log -Tail 200 | Out-Host
    Fail-And-Undo "DO command failed. Log: $log"
  }
}

# --- COMPILEALL ---
Write-Host "== COMPILEALL ==" -ForegroundColor Cyan
try {
  & $Py -c "import compileall; import sys; ok=compileall.compile_dir(r'$Src', quiet=1); print('compileall:', ok); sys.exit(0 if ok else 2)"
} catch {
  Fail-And-Undo "compileall failed"
}

# --- QUICK SELFTEST (instantiate ModuleProtoWidget) ---
Write-Host "== QUICK SELFTEST ==" -ForegroundColor Cyan
$test = Join-Path $Handoff ("agent_quicktest_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".py")
$testlog = $test + ".txt"

@"
import os, sys, traceback
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(PROJ, "src")
sys.path.insert(0, SRC)

from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

try:
    from tabs.module_proto_widget import ModuleProtoWidget
    w = ModuleProtoWidget(None)
    print("OK: instantiated ModuleProtoWidget")
    print("has _recalc:", hasattr(w, "_recalc"))
    print("has _sync_shelf_mode:", hasattr(w, "_sync_shelf_mode"))
    print("SELFTEST_OK")
except Exception:
    print(traceback.format_exc())
    raise
"@ | Set-Content -LiteralPath $test -Encoding UTF8

try {
  & $Py -u $test *>> $testlog
  $tail = Get-Content $testlog -Tail 80 | Out-String
  if($tail -notmatch "SELFTEST_OK"){ throw "SELFTEST missing marker" }
  Write-Host "✅ SELFTEST_OK" -ForegroundColor Green
} catch {
  Get-Content $testlog -Tail 200 | Out-Host
  Fail-And-Undo "quick selftest failed. Log: $testlog"
}

# --- RUN app (optional) ---
if($Run){
  Write-Host "== RUN ==" -ForegroundColor Cyan
  $env:PYTHONPATH = "$Src"
  & $Py (Join-Path $Src "main.py")
}

Write-Host "✅ DONE: step ok + compile ok + selftest ok" -ForegroundColor Green
