$ErrorActionPreference="Stop"
$Proj = Split-Path (Split-Path $PSCommandPath -Parent) -Parent
$LastFile = Join-Path (Join-Path $Proj "_undo") "LAST_STEP.txt"
if(-not (Test-Path $LastFile)){ throw "No LAST_STEP.txt found: $LastFile" }

$StepDir = (Get-Content -LiteralPath $LastFile -Raw).Trim()
if(-not $StepDir){ throw "LAST_STEP.txt is empty" }

$UndoPs = Join-Path $StepDir "UNDO.ps1"
if(-not (Test-Path $UndoPs)){ throw "UNDO.ps1 not found: $UndoPs" }

Write-Host "Undoing last step:"
Write-Host $UndoPs
powershell -ExecutionPolicy Bypass -File $UndoPs
