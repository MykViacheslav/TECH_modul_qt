param(
    [string]$Root = "C:\PythonProject\TECH_modul",
    [switch]$RunQuickTests,
    [switch]$RunAfterPatch
)

$ErrorActionPreference = "Stop"

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Text
    )
    $dir = Split-Path -Parent $Path
    if ($dir) { Ensure-Dir $dir }
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Copy-RelFile {
    param(
        [string]$ProjectRoot,
        [string]$BundleFilesRoot,
        [string]$RelativePath
    )

    $src = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path $src)) {
        return $false
    }

    $dst = Join-Path $BundleFilesRoot $RelativePath
    $dstDir = Split-Path -Parent $dst
    Ensure-Dir $dstDir
    Copy-Item -Path $src -Destination $dst -Force
    return $true
}

function Run-And-Save {
    param(
        [string]$FilePath,
        [scriptblock]$Action
    )

    try {
        $output = & $Action 2>&1 | Out-String
        Write-Utf8NoBom $FilePath $output
        return @{ Ok = $true; Output = $output }
    }
    catch {
        $msg = $_ | Out-String
        Write-Utf8NoBom $FilePath $msg
        return @{ Ok = $false; Output = $msg }
    }
}

if (-not (Test-Path $Root)) {
    throw "Nie widzę folderu projektu: $Root"
}

Set-Location $Root

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BundleRoot = Join-Path $Root ("tools\handoff_bundle_{0}" -f $Stamp)
$FilesRoot  = Join-Path $BundleRoot "files"
$MetaRoot   = Join-Path $BundleRoot "meta"
$LogsRoot   = Join-Path $BundleRoot "logs"
$ZipPath    = Join-Path $Root ("tools\handoff_bundle_{0}.zip" -f $Stamp)

Ensure-Dir $BundleRoot
Ensure-Dir $FilesRoot
Ensure-Dir $MetaRoot
Ensure-Dir $LogsRoot

$PythonExe = Join-Path $Root ".venv\Scripts\python.exe"
$HasPython = Test-Path $PythonExe

$KeyFiles = @(
    "src\tabs\modul\tab_modul.py",
    "src\app\main.py",
    "src\app\main_window.py",
    "src\tabs\registry.py",
    "src\ui\collapsible_block.py",
    "src\core\drawing_settings.py",
    "tools\after_patch.ps1",
    "tests\test_front_hardware_front_zone.py",
    "tests\test_tab_modul_temp_front_hide_preview.py",
    "tests\test_views_canvas_front_zone_render.py",
    "tests\test_canvas_front_layout_top_position.py",
    "tests\test_tab_modul_left_blocks_order.py",
    "tests\test_tab_modul_left_secondary_blocks_height_limits.py",
    "tests\test_tab_modul_tree_block_height_limit.py",
    "tests\test_tab_modul_secondary_left_blocks_collapsed_on_start.py",
    "tests\test_tab_modul_startup_canvas_fit.py",
    "tests\test_smoke.py",
    "tests\test_session_view_block_hides_hint_in_modul.py",
    "tests\test_session_view_block_hides_drawing_checkbox_in_modul.py"
)

$Copied = New-Object System.Collections.Generic.List[string]
$Missing = New-Object System.Collections.Generic.List[string]

foreach ($rel in $KeyFiles) {
    if (Copy-RelFile -ProjectRoot $Root -BundleFilesRoot $FilesRoot -RelativePath $rel) {
        [void]$Copied.Add($rel)
    }
    else {
        [void]$Missing.Add($rel)
    }
}

$TreeTargets = @(
    "src\tabs\modul",
    "src\app",
    "src\core",
    "src\ui",
    "tests",
    "tools"
)

$treeLines = New-Object System.Collections.Generic.List[string]
foreach ($target in $TreeTargets) {
    $abs = Join-Path $Root $target
    [void]$treeLines.Add(("=== {0} ===" -f $target))
    if (Test-Path $abs) {
        Get-ChildItem -Path $abs -Recurse -File |
            Sort-Object FullName |
            ForEach-Object {
                $rel = $_.FullName.Substring($Root.Length).TrimStart('\')
                [void]$treeLines.Add($rel)
            }
    }
    else {
        [void]$treeLines.Add("[BRAK] $target")
    }
    [void]$treeLines.Add("")
}
Write-Utf8NoBom (Join-Path $MetaRoot "01_project_tree.txt") ($treeLines -join [Environment]::NewLine)

$versions = New-Object System.Collections.Generic.List[string]
[void]$versions.Add(("Projekt: {0}" -f $Root))
[void]$versions.Add(("Data bundle: {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")))
[void]$versions.Add("")

if ($HasPython) {
    $pyVer = (& $PythonExe --version 2>&1 | Out-String).Trim()
    [void]$versions.Add(("Python: {0}" -f $pyVer))

    $qtInfo = (& $PythonExe -c "from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR; print(f'PyQt6 {PYQT_VERSION_STR} Qt {QT_VERSION_STR}')" 2>&1 | Out-String).Trim()
    [void]$versions.Add(("PyQt: {0}" -f $qtInfo))
}
else {
    [void]$versions.Add("Python: [BRAK] .venv\Scripts\python.exe")
}

$gitLines = New-Object System.Collections.Generic.List[string]
$gitExe = Get-Command git -ErrorAction SilentlyContinue
if ($gitExe) {
    try {
        $insideGit = (& git rev-parse --is-inside-work-tree 2>$null | Out-String).Trim()
        if ($insideGit -eq "true") {
            [void]$versions.Add(("Git commit: {0}" -f ((& git rev-parse --short HEAD | Out-String).Trim())))
            [void]$versions.Add("")
            [void]$gitLines.Add("=== git status --short ===")
            [void]$gitLines.Add(((& git status --short | Out-String).TrimEnd()))
            [void]$gitLines.Add("")
            [void]$gitLines.Add("=== git diff --stat ===")
            [void]$gitLines.Add(((& git diff --stat | Out-String).TrimEnd()))
        }
    }
    catch {
        [void]$gitLines.Add("Nie udało się pobrać danych z git.")
    }
}
Write-Utf8NoBom (Join-Path $MetaRoot "02_versions.txt") ($versions -join [Environment]::NewLine)
Write-Utf8NoBom (Join-Path $MetaRoot "03_git_info.txt") ($gitLines -join [Environment]::NewLine)

$recentFiles = Get-ChildItem -Path (Join-Path $Root "src"), (Join-Path $Root "tests"), (Join-Path $Root "tools") -Recurse -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 60 FullName, LastWriteTime

$recentLines = New-Object System.Collections.Generic.List[string]
foreach ($row in $recentFiles) {
    $rel = $row.FullName.Substring($Root.Length).TrimStart('\')
    [void]$recentLines.Add(("{0} | {1}" -f $row.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), $rel))
}
Write-Utf8NoBom (Join-Path $MetaRoot "04_recent_files.txt") ($recentLines -join [Environment]::NewLine)

$quickTests = @(
    "tests\test_canvas_front_layout_top_position.py",
    "tests\test_views_canvas_front_zone_render.py",
    "tests\test_tab_modul_temp_front_hide_preview.py"
)

$quickCmd = if ($HasPython) {
    "& `"$PythonExe`" -m pytest -q ``r``n    " + (($quickTests | ForEach-Object { $_ }) -join " ``r``n    ")
}
else {
    "[BRAK PYTHON EXE]"
}

$afterPatchCmd = "powershell -ExecutionPolicy Bypass -File .\tools\after_patch.ps1"

$commandsText = @"
SZYBKI PAKIET TESTÓW:
$quickCmd

PELNE SPRAWDZENIE:
$afterPatchCmd
"@
Write-Utf8NoBom (Join-Path $MetaRoot "05_commands.txt") $commandsText

if ($RunQuickTests -and $HasPython) {
    $args = @("-m", "pytest", "-q") + $quickTests
    $result = Run-And-Save -FilePath (Join-Path $LogsRoot "quick_tests.log") -Action { & $PythonExe @args }
    $quickSummary = if ($result.Ok) { "OK" } else { "ERROR" }
    Write-Utf8NoBom (Join-Path $LogsRoot "quick_tests_status.txt") $quickSummary
}

if ($RunAfterPatch) {
    $result = Run-And-Save -FilePath (Join-Path $LogsRoot "after_patch.log") -Action {
        powershell -ExecutionPolicy Bypass -File .\tools\after_patch.ps1
    }
    $afterSummary = if ($result.Ok) { "OK" } else { "ERROR" }
    Write-Utf8NoBom (Join-Path $LogsRoot "after_patch_status.txt") $afterSummary
}

$rulesText = @"
PRACA W NOWYM CHACIE:
1. Pisz po polsku albo po ukrainsku normalnie, bez dziwnego zargonu.
2. Ja nie jestem programista — tylko kopiuje to, co dostaje.
3. Dawaj tylko cale gotowe bloki do wklejenia albo caly plik.
4. Kazdy blok ma byc jasno podpisany:
   - SCIEZKA DO PLIKU
   - REGION / BLOK
   - CO DOKLADNIE ZAMIENIC
5. Pracujemy blokowo. Nie rozwalac innych czesci.
6. Pracujemy tylko przez PyCharm.
7. Po kazdej zmianie podawaj testy i uruchomienie aplikacji.
8. Najlepiej zawsze konczyc komenda:
   powershell -ExecutionPolicy Bypass -File .\tools\after_patch.ps1
9. GUI po polsku.
10. Nazwy techniczne / klucze / identyfikatory w kodzie po angielsku, bez polskich znakow.
"@
Write-Utf8NoBom (Join-Path $MetaRoot "06_rules.txt") $rulesText

$copiedListText = if ($Copied.Count -gt 0) {
    ($Copied | ForEach-Object { "- $_" }) -join [Environment]::NewLine
} else {
    "- [NIC NIE SKOPIOWANO]"
}

$missingListText = if ($Missing.Count -gt 0) {
    ($Missing | ForEach-Object { "- $_" }) -join [Environment]::NewLine
} else {
    "- brak"
}

$newChatText = @"
START NOWEGO CHATA

Pracujemy dalej nad projektem TECH_modul.
Nie startujemy od zera.
Wgralem ZIP z handoffem i tam sa kluczowe pliki, testy i opis.

NAJWAZNIEJSZY AKTUALNY STAN:
- ostatni stan byl zielony
- aplikacja sie uruchamiala
- front zone zostal dopiety roboczo
- tymczasowe ukrywanie frontu w preview dziala roboczo
- render frontu w widoku z gory zostal naprawiony
- byly naprawiane problemy: brak self.tree, brak self.ref, kolejnosc blokow po lewej, wysokosci blokow, helper frontu w top-view
- pola typu front_height_mode / front_offset_top_mm / front_offset_bottom_mm sa aktualnie traktowane roboczo przez getattr/setattr na draft, zeby nie wywalac replace() dataclass

CO JEST NAJWAZNIEJSZE TERAZ:
1. Dokonczyc wygodny, czytelny UI do chwilowego ukrywania frontu w zakladce Moduł.
2. Dopiac logike offset_top / offset_bottom jako normalna czesc pracy.
3. Przygotowac grunt pod przesuwanie strefy frontu myszka.
4. Nie rozwalic obecnych testow i stabilnosci.

KLUCZOWY PLIK:
- src\tabs\modul\tab_modul.py

KLUCZOWE TESTY:
- tests\test_front_hardware_front_zone.py
- tests\test_tab_modul_temp_front_hide_preview.py
- tests\test_views_canvas_front_zone_render.py
- tests\test_canvas_front_layout_top_position.py

JAK MASZ MI ODPOWIADAC:
- dawaj gotowy blok do wklejenia albo caly plik
- zawsze podpisz: SCIEZKA / REGION / CO ZAMIENIC
- po zmianie podaj testy
- po zmianie podaj tez:
  powershell -ExecutionPolicy Bypass -File .\tools\after_patch.ps1

TERAZ JEDZIEMY OD TEGO:
Zrob krok 1: czytelny UI do tymczasowego ukrycia frontu w zakladce Moduł, blokowo i bez psucia testow.

PLIKI DOLACZONE W BUNDLE:
$copiedListText

BRAKUJACE Z LISTY OCZEKIWANEJ:
$missingListText

KONIEC STARTU NOWEGO CHATA
"@
Write-Utf8NoBom (Join-Path $BundleRoot "00_NEW_CHAT_START.txt") $newChatText

$readmeText = @"
CO ZROBIL TEN SKRYPT:
1. Skopiowal kluczowe pliki projektu do folderu handoff.
2. Zapisal drzewo projektu, wersje, komendy i ostatnio zmieniane pliki.
3. Przygotowal gotowy tekst startowy do nowego chata.
4. Spakowal wszystko do ZIP.

CO ZROBIC TERAZ:
1. Otworz plik:
   $BundleRoot\00_NEW_CHAT_START.txt
2. W nowym chacie wgraj ZIP:
   $ZipPath
3. Wklej zawartosc 00_NEW_CHAT_START.txt
4. Napisz jedno zdanie:
   Jedziemy od kroku 1.

JESLI CHCESZ DOGRAC LOGI TESTOW:
- szybkie testy:
  powershell -ExecutionPolicy Bypass -File .\tools\make_handoff_bundle.ps1 -RunQuickTests
- pelny pakiet z after_patch:
  powershell -ExecutionPolicy Bypass -File .\tools\make_handoff_bundle.ps1 -RunAfterPatch
"@
Write-Utf8NoBom (Join-Path $BundleRoot "README_JAK_UZYC.txt") $readmeText

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $BundleRoot "*") -DestinationPath $ZipPath -Force

try {
    if (Get-Command Set-Clipboard -ErrorAction SilentlyContinue) {
        Set-Clipboard -Value (Get-Content -Raw (Join-Path $BundleRoot "00_NEW_CHAT_START.txt"))
    }
}
catch {
}

Write-Host ""
Write-Host "=== HANDOFF GOTOWY ===" -ForegroundColor Green
Write-Host "Folder: $BundleRoot"
Write-Host "ZIP:    $ZipPath"
Write-Host "Start:  $(Join-Path $BundleRoot '00_NEW_CHAT_START.txt')"
Write-Host ""
Write-Host "W nowym chacie:" -ForegroundColor Yellow
Write-Host "1) wgraj ZIP"
Write-Host "2) wklej zawartosc 00_NEW_CHAT_START.txt"
Write-Host "3) dopisz: Jedziemy od kroku 1."
Write-Host ""