param(
    [string]$Prompt = "napisz kod",
    [string]$Model = "phi3:mini",
    [switch]$RunTests,
    [switch]$StartApp
)

[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "C:\PythonProject\TECH_modul"
$BackupRoot = Join-Path $ProjectRoot "backups"
$TempFile = Join-Path $ProjectRoot "ai_last_output.txt"

function Backup-File($FilePath) {
    if (!(Test-Path $FilePath)) {
        return
    }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $name = Split-Path $FilePath -Leaf
    $destDir = Join-Path $BackupRoot $stamp

    New-Item -ItemType Directory -Force $destDir | Out-Null
    Copy-Item $FilePath (Join-Path $destDir $name) -Force
}

function Write-Utf8NoBom($Path, $Content) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Normalize-GeneratedCode($Text) {
    if ($null -eq $Text) {
        return ""
    }

    $result = $Text
    $result = [regex]::Replace($result, '^\s*```[a-zA-Z0-9_-]*\s*', '')
    $result = [regex]::Replace($result, '\s*```\s*$', '')
    $result = $result -replace "`r`n", "`n"
    $result = $result -replace "`r", "`n"
    $result = $result.Trim("`n")

    return $result + "`n"
}

$SystemPrompt = @"
Pisz po polsku.

WAZNE ZASADY:
- zwracaj tylko gotowe pliki
- bez wyjasnien
- bez komentarza przed plikiem
- bez komentarza po pliku
- bez blokow ```python
- bez markdown
- bez skrotow
- bez pomijania importow
- GUI po polsku
- identyfikatory techniczne po angielsku

ZWROC TYLKO TEN FORMAT:
===FILE: sciezka/do/pliku.py===
pelny kod
===END===

NIE DOPISUJ NIC POZA TYM FORMATEM.
"@

$FullPrompt = $SystemPrompt + "`r`n" + $Prompt

Write-Host ">> Generowanie kodu przez AI..."
ollama run $Model $FullPrompt | Tee-Object -FilePath $TempFile

$content = Get-Content $TempFile -Raw -Encoding UTF8
$pattern = "(?s)===FILE:(.*?)===(.*?)===END==="
$matches = [regex]::Matches($content, $pattern)

if ($matches.Count -eq 0) {
    Write-Host ""
    Write-Host "ERROR: Nie znaleziono poprawnego formatu."
    Write-Host "Sprawdz plik: $TempFile"
    exit 1
}

foreach ($m in $matches) {
    $relativePath = $m.Groups[1].Value.Trim()
    $fileContent = $m.Groups[2].Value
    $fileContent = Normalize-GeneratedCode $fileContent

    $fullPath = Join-Path $ProjectRoot $relativePath

    Write-Host ""
    Write-Host ">>> Plik: $relativePath"

    Backup-File $fullPath

    $dir = Split-Path $fullPath -Parent
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Force $dir | Out-Null
    }

    Write-Utf8NoBom $fullPath $fileContent
    Write-Host "OK: zapisano plik (UTF-8, bez markdown fence)"
}

$Py = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if ($RunTests) {
    Write-Host ""
    Write-Host ">> TESTY"

    if (Test-Path $Py) {
        $TestsPath = Join-Path $ProjectRoot "tests"
        if (Test-Path $TestsPath) {
            Push-Location $ProjectRoot
            try {
                & $Py -m pytest $TestsPath
            }
            finally {
                Pop-Location
            }
        }
        else {
            Write-Host "Brak folderu tests"
        }
    }
    else {
        Write-Host "ERROR: Brak python .venv"
    }
}

if ($StartApp) {
    Write-Host ""
    Write-Host ">> START APP"

    if (Test-Path $Py) {
        Push-Location $ProjectRoot
        try {
            & $Py -m src.app.main
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Host "ERROR: Brak python .venv"
    }
}