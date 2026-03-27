param(
    [string]$ProjectRoot = ".",
    [string]$VenvPython = "",
    [string]$MainPy = ""
)

$ErrorActionPreference = "Stop"

# ----------------------------------------------------------
# HELPERS
# ----------------------------------------------------------

function Write-File {
    param($Path, $Text)
    $dir = Split-Path $Path
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $Text | Out-File -Encoding utf8 -FilePath $Path
}

function Run {
    param($cmd)

    Write-Host "RUN: $cmd" -ForegroundColor Cyan
    try {
        $out = Invoke-Expression $cmd 2>&1
        return $out
    }
    catch {
        return $_
    }
}

function Get-Python {
    param($root, $preferred)

    if ($preferred -and (Test-Path $preferred)) {
        return (Resolve-Path $preferred).Path
    }

    $venv = Join-Path $root ".venv\Scripts\python.exe"
    if (Test-Path $venv) {
        return $venv
    }

    return "python"
}

# ----------------------------------------------------------
# INIT
# ----------------------------------------------------------

$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$Py = Get-Python $ProjectRoot $VenvPython

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Out = Join-Path $ProjectRoot "tools\audit_out\audit_$Stamp"

New-Item -ItemType Directory -Force $Out | Out-Null

# ----------------------------------------------------------
# FILE LIST (🔥 BEZ .venv)
# ----------------------------------------------------------

$Exclude = @(".venv", ".git", "__pycache__", ".idea", ".pytest_cache")

$Files = Get-ChildItem -Recurse -File | Where-Object {
    $full = $_.FullName
    foreach ($e in $Exclude) {
        if ($full -like "*\$e*") { return $false }
    }
    return $true
}

$PyFiles = $Files | Where-Object { $_.Extension -eq ".py" }

Write-Host "PY FILES: $($PyFiles.Count)" -ForegroundColor Yellow

# ----------------------------------------------------------
# SYNTAX CHECK
# ----------------------------------------------------------

$syntax = @()

foreach ($f in $PyFiles) {
    $cmd = "$Py -m py_compile `"$($f.FullName)`""
    $res = Run $cmd

    if ($LASTEXITCODE -eq 0) {
        $syntax += "[OK] $($f.FullName)"
    }
    else {
        $syntax += "[ERR] $($f.FullName)"
        $syntax += $res
    }
}

Write-File "$Out\04_syntax.txt" ($syntax -join "`n")

# ----------------------------------------------------------
# IMPORT CHECK
# ----------------------------------------------------------

$import = @()

foreach ($f in $PyFiles) {
    $cmd = "$Py `"$($f.FullName)`""
    $res = Run $cmd

    if ($LASTEXITCODE -eq 0) {
        $import += "[OK] $($f.FullName)"
    }
    else {
        $import += "[ERR] $($f.FullName)"
        $import += $res
    }
}

Write-File "$Out\05_import.txt" ($import -join "`n")

# ----------------------------------------------------------
# PYTEST
# ----------------------------------------------------------

$pytest = Run "$Py -m pytest -q"
Write-File "$Out\06_pytest.txt" ($pytest -join "`n")

# ----------------------------------------------------------
# RUN APP
# ----------------------------------------------------------

if ($MainPy) {
    $MainFull = Join-Path $ProjectRoot $MainPy
    $app = Run "$Py `"$MainFull`""
    Write-File "$Out\07_run.txt" ($app -join "`n")
}

# ----------------------------------------------------------
# SUMMARY
# ----------------------------------------------------------

$sum = @()
$sum += "FILES: $($Files.Count)"
$sum += "PY: $($PyFiles.Count)"
$sum += "OUT: $Out"

Write-File "$Out\00_summary.txt" ($sum -join "`n")

Write-Host ""
Write-Host "AUDIT DONE:" -ForegroundColor Green
Write-Host $Out -ForegroundColor Yellow