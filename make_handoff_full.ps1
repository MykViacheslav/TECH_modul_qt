$ErrorActionPreference="Stop"

# ------------------ CONFIG ------------------
$proj="C:\PythonProject\TECH_modul\TECH_modul_qt"
$py=Join-Path $proj ".venv\Scripts\python.exe"
$mod=Join-Path $proj "src\tabs\module_widget.py"

$rootOut=Join-Path $proj "_handoff"
New-Item -ItemType Directory -Force -Path $rootOut | Out-Null

$stamp=Get-Date -Format "yyyyMMdd_HHmmss"
$pkgDir=Join-Path $rootOut ("pkg_" + $stamp)
New-Item -ItemType Directory -Force -Path $pkgDir | Out-Null

# ------------------ HELPERS ------------------
function Write-UTF8([string]$path, [string]$text) {
  $parent = Split-Path -Parent $path
  if ($parent -and !(Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  $text | Set-Content -Encoding UTF8 -Path $path
}

function Append-UTF8([string]$path, [string]$text) {
  $parent = Split-Path -Parent $path
  if ($parent -and !(Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  $text | Add-Content -Encoding UTF8 -Path $path
}

function Add-CodeBlockToMd([string]$mdPath, [string]$filePath, [string]$lang) {
  if (Test-Path $filePath) {
    Append-UTF8 $mdPath ""
    Append-UTF8 $mdPath ("## " + $filePath)
    Append-UTF8 $mdPath ("~~~" + $lang)
    Get-Content -Path $filePath | Add-Content -Encoding UTF8 -Path $mdPath
    Append-UTF8 $mdPath "~~~"
  }
}

# ------------------ README + SUMMARY ------------------
$readme = Join-Path $pkgDir "README.md"
Write-UTF8 $readme @"
# TECH_modul_qt — handoff package ($stamp)

## Upload to new chat
1) Upload the ZIP from _handoff\
2) Paste SUMMARY.md text into message

## Contents
- SUMMARY.md
- DIAG.txt
- FILELIST.txt
- BUNDLE.md (key sources)
- backups\ (module_widget.py.bak_*)
- patches\ (_patch_*.py)
- snapshot\ (selected project files)

## Dev rule
- Change ONLY one tab/section at a time.
- Every change via PowerShell: backup + py_compile + pytest.
"@

$summary = Join-Path $pkgDir "SUMMARY.md"
Write-UTF8 $summary @"
# SUMMARY ($stamp)

## Now works
- (fill)

## Broken / missing
- (fill)

## Last symptoms
- (fill)

## Next goal
- (fill)

## Notes
- Many auto-patches happened; UI sometimes disappears.
- Prefer isolated edits per tab/section.
"@

# ------------------ SNAPSHOT ------------------
$snapDir = Join-Path $pkgDir "snapshot"
New-Item -ItemType Directory -Force -Path $snapDir | Out-Null

$copyList = @(
  "src\tabs\module_widget.py",
  "src\tabs\registry.py",
  "src\tabs\tab_module.py",
  "src\main.py",
  "src\app\main_window.py",
  "src\app\run_shell.py",
  "data\modules.json",
  "tests\test_core_math.py",
  "tests\test_drawer_nl.py"
)

foreach ($rel in $copyList) {
  $src = Join-Path $proj $rel
  if (Test-Path $src) {
    $dst = Join-Path $snapDir $rel
    $dstParent = Split-Path -Parent $dst
    New-Item -ItemType Directory -Force -Path $dstParent | Out-Null
    Copy-Item -Force $src $dst
  }
}

# ------------------ BACKUPS + PATCHES ------------------
$bakDir = Join-Path $pkgDir "backups"
New-Item -ItemType Directory -Force -Path $bakDir | Out-Null

$modDir = Split-Path -Parent $mod
Get-ChildItem -Path $modDir -Filter "module_widget.py.bak_*" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime |
  ForEach-Object { Copy-Item -Force $_.FullName $bakDir }

$patchDir = Join-Path $pkgDir "patches"
New-Item -ItemType Directory -Force -Path $patchDir | Out-Null
Get-ChildItem -Path $proj -Filter "_patch_*.py" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime |
  ForEach-Object { Copy-Item -Force $_.FullName $patchDir }

# ------------------ DIAGNOSTICS (TXT) ------------------
$diag = Join-Path $pkgDir "DIAG.txt"
Write-UTF8 $diag ("stamp: " + $stamp + "`r`nproj: " + $proj + "`r`npython: " + $py + "`r`nmod: " + $mod + "`r`n")

Append-UTF8 $diag "`r`n== python --version =="
(& $py --version 2>&1) | ForEach-Object { $_ } | Add-Content -Encoding UTF8 -Path $diag

Append-UTF8 $diag "`r`n== py_compile module_widget.py =="
try { (& $py -m py_compile $mod 2>&1) | ForEach-Object { $_ } | Add-Content -Encoding UTF8 -Path $diag }
catch { Append-UTF8 $diag ("py_compile FAILED: " + $_.Exception.Message) }

Append-UTF8 $diag "`r`n== pytest -q =="
try {
  chcp 65001 | Out-Null
  $env:PYTHONIOENCODING="utf-8"
  $env:PYTHONPATH = (Join-Path $proj "src")
  (& $py -m pytest -q 2>&1) | ForEach-Object { $_ } | Add-Content -Encoding UTF8 -Path $diag
} catch {
  Append-UTF8 $diag ("pytest FAILED: " + $_.Exception.Message)
}

# ------------------ FILELIST ------------------
$filelist = Join-Path $pkgDir "FILELIST.txt"
Write-UTF8 $filelist ("Files included (" + $stamp + ")`r`n")

Get-ChildItem -Recurse -File $pkgDir | ForEach-Object {
  $rel = $_.FullName.Replace($pkgDir + "\", "")
  Add-Content -Encoding UTF8 -Path $filelist -Value ("- " + $rel)
}

# ------------------ BUNDLE.MD ------------------
$bundle = Join-Path $pkgDir "BUNDLE.md"
Write-UTF8 $bundle ("# Source bundle (" + $stamp + ")`r`nProject: " + $proj + "`r`n")

$bundleFiles = @(
  "src\tabs\module_widget.py",
  "src\tabs\tab_module.py",
  "src\tabs\registry.py",
  "data\modules.json",
  "tests\test_core_math.py",
  "tests\test_drawer_nl.py"
)

foreach ($rel in $bundleFiles) {
  $path = Join-Path $proj $rel
  Add-CodeBlockToMd $bundle $path "python"
}

# ------------------ ZIP ------------------
$zipPath = Join-Path $rootOut ("TECH_modul_qt_handoff_" + $stamp + ".zip")
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $pkgDir "*") -DestinationPath $zipPath -Force

Write-Host ""
Write-Host "DONE ✅"
Write-Host "Folder: $pkgDir"
Write-Host "ZIP:    $zipPath"
