param(
  [Parameter(Mandatory=$true)]
  [string]$Zip
)

$ErrorActionPreference = "Stop"

function Get-ProjectRoot {
  param([string]$StartDir)

  $p = (Resolve-Path $StartDir).Path
  for ($i = 0; $i -lt 8; $i++) {
    if ((Test-Path (Join-Path $p "src")) -and (Test-Path (Join-Path $p "tools"))) {
      return $p
    }
    $parent = Split-Path $p -Parent
    if ($parent -eq $p) { break }
    $p = $parent
  }
  throw "Nie mogę znaleźć root projektu (szukam folderów: src i tools). Start: $StartDir"
}

$start = if ($PSScriptRoot -and $PSScriptRoot.Trim()) { (Join-Path $PSScriptRoot "..") } else { (Get-Location).Path }
$Proj = Get-ProjectRoot $start

# znajdź zip (może być względny lub absolutny)
$ZipPath = $null
try { $ZipPath = (Resolve-Path (Join-Path $Proj $Zip) -ErrorAction SilentlyContinue) } catch {}
if (-not $ZipPath) {
  try { $ZipPath = (Resolve-Path $Zip -ErrorAction SilentlyContinue) } catch {}
}
if (-not $ZipPath) { throw "Nie widzę zipa: $Zip" }
$ZipPath = $ZipPath.Path

# Backup aktualnego stanu (przed restore)
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = Join-Path $Proj "archiw\restore_backup_$Stamp"
New-Item -ItemType Directory -Force $BackupRoot | Out-Null

$ToBackup = @("src","tests","tools","data","pytest.ini","requirements.txt","README_PL.md",".gitignore")
foreach ($p in $ToBackup) {
  $srcPath = Join-Path $Proj $p
  if (Test-Path $srcPath) {
    $dstPath = Join-Path $BackupRoot $p
    if (Test-Path $srcPath -PathType Container) {
      New-Item -ItemType Directory -Force $dstPath | Out-Null
      robocopy $srcPath $dstPath /E /NFL /NDL /NJH /NJS | Out-Null
    } else {
      New-Item -ItemType Directory -Force (Split-Path -Parent $dstPath) | Out-Null
      Copy-Item -Force $srcPath $dstPath
    }
  }
}

# Rozpakuj do temp
$tmp = Join-Path $env:TEMP ("tech_modul_restore_" + $Stamp)
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
New-Item -ItemType Directory -Force $tmp | Out-Null

Expand-Archive -Path $ZipPath -DestinationPath $tmp -Force

function CopyDir($from, $to) {
  if (Test-Path $from) {
    New-Item -ItemType Directory -Force $to | Out-Null
    robocopy $from $to /E /NFL /NDL /NJH /NJS | Out-Null
  }
}

CopyDir (Join-Path $tmp "src")   (Join-Path $Proj "src")
CopyDir (Join-Path $tmp "tests") (Join-Path $Proj "tests")
CopyDir (Join-Path $tmp "tools") (Join-Path $Proj "tools")
CopyDir (Join-Path $tmp "data")  (Join-Path $Proj "data")

foreach ($f in @("pytest.ini","requirements.txt","README_PL.md",".gitignore")) {
  $ff = Join-Path $tmp $f
  if (Test-Path $ff) {
    Copy-Item -Force $ff (Join-Path $Proj $f)
  }
}

Write-Host ""
Write-Host "OK. Przywrócono snapshot z:"
Write-Host " - $ZipPath"
Write-Host ""
Write-Host "Backup poprzedniego stanu jest tu:"
Write-Host " - $BackupRoot"
Write-Host ""
Write-Host "Odpal teraz testy i app:"
Write-Host "cd `"$Proj`""
Write-Host ".\tools\after_patch.ps1"