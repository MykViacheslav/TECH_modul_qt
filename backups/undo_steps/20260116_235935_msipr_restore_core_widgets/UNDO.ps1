$ErrorActionPreference = "Stop"
$Proj = "C:\PythonProject\TECH_modul\TECH_modul_qt"
$StepDir = "C:\PythonProject\TECH_modul\TECH_modul_qt\backups\undo_steps\20260116_235935_msipr_restore_core_widgets"
Set-Location $Proj

function Restore-Dir([string]$rel){
  $src = Join-Path $StepDir $rel
  $dst = Join-Path $Proj    $rel
  if (Test-Path $src){
    if (Test-Path $dst){ Remove-Item $dst -Recurse -Force }
    Copy-Item $src $dst -Recurse -Force
    Write-Host "Restored: $dst"
  } else {
    if (Test-Path $dst){
      Remove-Item $dst -Recurse -Force
      Write-Host "Removed: $dst (was created in this step)"
    }
  }
}

Restore-Dir "src\core"
Restore-Dir "src\widgets"

Write-Host ""
Write-Host "✅ UNDO done. step=C:\PythonProject\TECH_modul\TECH_modul_qt\backups\undo_steps\20260116_235935_msipr_restore_core_widgets"
