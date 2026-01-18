param(
  [Parameter(Mandatory=$true)]
  [string[]]$Files,
  [string]$Note = ""
)

$ErrorActionPreference="Stop"
$Proj = Split-Path (Split-Path $PSCommandPath -Parent) -Parent

$UndoRoot = Join-Path $Proj "_undo"
if(-not (Test-Path $UndoRoot)){ New-Item -ItemType Directory -Path $UndoRoot | Out-Null }

$StepsRoot = Join-Path $UndoRoot "steps"
if(-not (Test-Path $StepsRoot)){ New-Item -ItemType Directory -Path $StepsRoot | Out-Null }

$stamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$StepDir = Join-Path $StepsRoot ("step_" + $stamp)
New-Item -ItemType Directory -Path $StepDir | Out-Null

# meta files
$presentList = Join-Path $StepDir "FILES_PRESENT.txt"
$missingList = Join-Path $StepDir "MISSING_BEFORE.txt"
$noteFile    = Join-Path $StepDir "NOTE.txt"

Set-Content -LiteralPath $presentList -Value "" -Encoding UTF8
Set-Content -LiteralPath $missingList -Value "" -Encoding UTF8
Set-Content -LiteralPath $noteFile    -Value $Note -Encoding UTF8

function Add-Line([string]$path, [string]$line){
  Add-Content -LiteralPath $path -Value $line -Encoding UTF8
}

function Copy-ForStep([string]$rel){
  $rel = $rel.TrimStart('\','/')
  $abs = Join-Path $Proj $rel

  if(Test-Path $abs){
    Add-Line $presentList $rel

    $dst = Join-Path $StepDir $rel
    $dstDir = Split-Path $dst -Parent
    if(-not (Test-Path $dstDir)){ New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }

    if((Get-Item -LiteralPath $abs).PSIsContainer){
      Copy-Item -LiteralPath $abs -Destination $dst -Recurse -Force
    } else {
      Copy-Item -LiteralPath $abs -Destination $dst -Force
    }
  } else {
    Add-Line $missingList $rel
  }
}

foreach($f in $Files){
  Copy-ForStep $f
}

# UNDO.ps1 (restores backed up items; removes items that were missing before the step)
$UndoPs = Join-Path $StepDir "UNDO.ps1"
@"
`$ErrorActionPreference="Stop"
`$Proj = "$Proj"
`$StepDir = "$StepDir"

function Restore-One([string]`$rel){
  `$rel = `$rel.TrimStart('\','/')
  `$src = Join-Path `$StepDir `$rel
  `$dst = Join-Path `$Proj  `$rel
  if(-not (Test-Path `$src)){ return }

  if((Get-Item -LiteralPath `$src).PSIsContainer){
    if(Test-Path `$dst){ Remove-Item -LiteralPath `$dst -Recurse -Force }
    `$dstDir = Split-Path `$dst -Parent
    if(-not (Test-Path `$dstDir)){ New-Item -ItemType Directory -Path `$dstDir -Force | Out-Null }
    Copy-Item -LiteralPath `$src -Destination `$dst -Recurse -Force
  } else {
    `$dstDir = Split-Path `$dst -Parent
    if(-not (Test-Path `$dstDir)){ New-Item -ItemType Directory -Path `$dstDir -Force | Out-Null }
    Copy-Item -LiteralPath `$src -Destination `$dst -Force
  }
}

# restore all that existed before
`$present = Get-Content -LiteralPath (Join-Path `$StepDir "FILES_PRESENT.txt") -ErrorAction SilentlyContinue
foreach(`$rel in `$present){
  if(`$rel -and `$rel.Trim().Length -gt 0){ Restore-One `$rel }
}

# remove what did NOT exist before this step (if created during the step)
`$missing = Get-Content -LiteralPath (Join-Path `$StepDir "MISSING_BEFORE.txt") -ErrorAction SilentlyContinue
foreach(`$rel in `$missing){
  if(-not `$rel){ continue }
  `$rel = `$rel.Trim()
  if(`$rel.Length -eq 0){ continue }
  `$dst = Join-Path `$Proj `$rel
  if(Test-Path `$dst){
    if((Get-Item -LiteralPath `$dst).PSIsContainer){
      Remove-Item -LiteralPath `$dst -Recurse -Force -ErrorAction SilentlyContinue
    } else {
      Remove-Item -LiteralPath `$dst -Force -ErrorAction SilentlyContinue
    }
  }
}

Write-Host "UNDO OK. Restored from: `$StepDir"
"@ | Set-Content -LiteralPath $UndoPs -Encoding UTF8

# mark LAST_STEP
Set-Content -LiteralPath (Join-Path $UndoRoot "LAST_STEP.txt") -Value $StepDir -Encoding UTF8

Write-Host "✅ STEP created: $StepDir"
Write-Host "🧯 Undo command:"
Write-Host ("powershell -ExecutionPolicy Bypass -File `"" + $UndoPs + "`"")
