# Uruchamia briefing_start.bat bez widocznego okna
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BatFile = Join-Path $ProjectRoot "tools\briefing_start.bat"

if (Test-Path $BatFile) {
    # Uruchom BAT w ukrytym oknie
    & cmd.exe /c $BatFile
}
