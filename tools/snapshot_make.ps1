param(
  [string]$Label = ""
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

# Start: jeśli skrypt uruchomiony jako plik -> PSScriptRoot istnieje,
# jeśli ktoś odpalił z konsoli -> bierzemy bieżący katalog.
$start = if ($PSScriptRoot -and $PSScriptRoot.Trim()) { (Join-Path $PSScriptRoot "..") } else { (Get-Location).Path }
$Proj = Get-ProjectRoot $start

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$SafeLabel = $Label.Trim()
if ($SafeLabel) {
  $SafeLabel = ($SafeLabel -replace '[^\w\-]+','_')
  $SnapName = "SNAPSHOT_{0}_{1}" -f $Stamp, $SafeLabel
} else {
  $SnapName = "SNAPSHOT_{0}" -f $Stamp
}

$SnapRoot = Join-Path $Proj "archiw\snapshots\$SnapName"
New-Item -ItemType Directory -Force $SnapRoot | Out-Null

$ZipPath  = Join-Path $SnapRoot "snapshot.zip"
$Manifest = Join-Path $SnapRoot "manifest.txt"

# Co pakujemy (bez .venv)
$Paths = @(
  (Join-Path $Proj "src"),
  (Join-Path $Proj "tests"),
  (Join-Path $Proj "tools"),
  (Join-Path $Proj "data"),
  (Join-Path $Proj "pytest.ini"),
  (Join-Path $Proj "requirements.txt"),
  (Join-Path $Proj "README_PL.md"),
  (Join-Path $Proj ".gitignore")
) | Where-Object { Test-Path $_ }

if (-not $Paths -or $Paths.Count -eq 0) {
  throw "Nie mam nic do spakowania (Paths puste). Root projektu: $Proj"
}

# Manifest
$pyVer = ""
try { $pyVer = & python --version 2>&1 } catch { $pyVer = "" }

$lines = @()
$lines += "SNAPSHOT: $SnapName"
$lines += "DATE:     $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += "PROJECT:  $Proj"
if ($pyVer) { $lines += "PYTHON:   $pyVer" }
$lines += ""
$lines += "INCLUDED PATHS:"
$Paths | ForEach-Object { $lines += " - $($_)" }
$lines += ""

Set-Content -Path $Manifest -Value $lines -Encoding UTF8

# Zip
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path $Paths -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "OK. Snapshot gotowy:"
Write-Host " - $ZipPath"
Write-Host " - $Manifest"
Write-Host ""
Write-Host "Aby przywrócić:"
Write-Host "  .\tools\snapshot_restore.ps1 -Zip `"$ZipPath`""