param(
  [string]$Msg = "step"
)

$ErrorActionPreference="Stop"
$Proj = Split-Path -Parent $PSScriptRoot
Set-Location $Proj

$Src   = Join-Path $Proj "src"
$Venv  = Join-Path $Proj ".venv"
$Py    = Join-Path $Venv "Scripts\python.exe"
$Step  = Join-Path $PSScriptRoot "step.ps1"
$Test  = Join-Path $PSScriptRoot "selftest.ps1"
$Undo  = Join-Path $PSScriptRoot "undo_last.ps1"

Write-Host "PWD: $(Get-Location)"

if(Test-Path $Step){
  Write-Host "`n== STEP ==" -ForegroundColor Cyan
  powershell -ExecutionPolicy Bypass -File $Step $Msg
}else{
  Write-Host "WARN: tools\step.ps1 not found"
}

if(Test-Path $Test){
  Write-Host "`n== SELFTEST ==" -ForegroundColor Cyan
  powershell -ExecutionPolicy Bypass -File $Test
  if($LASTEXITCODE -ne 0){
    Write-Host "`n❌ SELFTEST FAILED (exitcode=$LASTEXITCODE)" -ForegroundColor Red
    if(Test-Path $Undo){
      Write-Host "UNDO:" -ForegroundColor Yellow
      Write-Host "powershell -ExecutionPolicy Bypass -File `"$Undo`""
    }
    exit 1
  }
}else{
  Write-Host "WARN: tools\selftest.ps1 not found"
}

Write-Host "`n== RUN ==" -ForegroundColor Cyan
$env:PYTHONPATH = "$Src"
& $Py (Join-Path $Src "main.py")
