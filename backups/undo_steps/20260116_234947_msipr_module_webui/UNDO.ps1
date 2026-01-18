$ErrorActionPreference = "Stop"
$Proj = "C:\PythonProject\TECH_modul\TECH_modul_qt"
$StepDir = "C:\PythonProject\TECH_modul\TECH_modul_qt\backups\undo_steps\20260116_234947_msipr_module_webui"

Set-Location $Proj

# restore tab_module.py
$src1 = Join-Path $StepDir "src\tabs\tab_module.py"
$dst1 = Join-Path $Proj    "src\tabs\tab_module.py"
if (Test-Path $src1) {
  Copy-Item -LiteralPath $src1 -Destination $dst1 -Force
  Write-Host "Restored: $dst1"
}

# restore webui folder (if it existed in backup); otherwise remove current webui
$srcWeb = Join-Path $StepDir "src\webui"
$dstWeb = Join-Path $Proj    "src\webui"
if (Test-Path $srcWeb) {
  if (Test-Path $dstWeb) { Remove-Item $dstWeb -Recurse -Force }
  Copy-Item -LiteralPath $srcWeb -Destination $dstWeb -Recurse -Force
  Write-Host "Restored: $dstWeb"
} else {
  if (Test-Path $dstWeb) {
    Remove-Item $dstWeb -Recurse -Force
    Write-Host "Removed: $dstWeb (was not present before this step)"
  }
}

Write-Host ""
Write-Host "✅ UNDO done. (step: C:\PythonProject\TECH_modul\TECH_modul_qt\backups\undo_steps\20260116_234947_msipr_module_webui)"