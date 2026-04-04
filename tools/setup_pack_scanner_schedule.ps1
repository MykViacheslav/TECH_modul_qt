param(
    [string]$StartAt = "06:00",
    [string]$StopAt = "22:00",
    [switch]$NoAutoStop
)

$ErrorActionPreference = "Stop"

$TaskStart = "TECH_modul PackScanner START"
$TaskStop = "TECH_modul PackScanner STOP"
$StartScript = Join-Path $PSScriptRoot "start_pack_scanner_server.ps1"
$StopScript = Join-Path $PSScriptRoot "stop_pack_scanner_server.ps1"

if (!(Test-Path $StartScript)) {
    throw "Brak pliku: $StartScript"
}
if (!(Test-Path $StopScript)) {
    throw "Brak pliku: $StopScript"
}

$startCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
$stopCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$StopScript`""

function Invoke-CmdQuiet([string]$line) {
    cmd.exe /c $line | Out-Null
    return $LASTEXITCODE
}

$null = Invoke-CmdQuiet "schtasks /Delete /TN `"$TaskStart`" /F >nul 2>nul"
$createStartCode = Invoke-CmdQuiet "schtasks /Create /TN `"$TaskStart`" /SC DAILY /ST $StartAt /TR `"$startCmd`" /RL LIMITED /F"
if ($createStartCode -ne 0) {
    throw "Nie udalo sie utworzyc zadania START (kod=$createStartCode)."
}

if ($NoAutoStop) {
    $null = Invoke-CmdQuiet "schtasks /Delete /TN `"$TaskStop`" /F >nul 2>nul"
} else {
    $null = Invoke-CmdQuiet "schtasks /Delete /TN `"$TaskStop`" /F >nul 2>nul"
    $createStopCode = Invoke-CmdQuiet "schtasks /Create /TN `"$TaskStop`" /SC DAILY /ST $StopAt /TR `"$stopCmd`" /RL LIMITED /F"
    if ($createStopCode -ne 0) {
        throw "Nie udalo sie utworzyc zadania STOP (kod=$createStopCode)."
    }
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host " Harmonogram Pack Scanner gotowy" -ForegroundColor Green
Write-Host " START: $StartAt (zadanie: $TaskStart)" -ForegroundColor Green
if ($NoAutoStop) {
    Write-Host " STOP:  wylaczony (serwer bedzie pracowal stale)" -ForegroundColor Yellow
} else {
    Write-Host " STOP:  $StopAt (zadanie: $TaskStop)" -ForegroundColor Green
}
Write-Host "===============================================" -ForegroundColor Green
Write-Host " URL skanera: https://[IP_KOMPUTERA]:9443/pack-scanner" -ForegroundColor Cyan
Write-Host ""
Write-Host "Aby uruchomic od razu teraz:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$StartScript`"" -ForegroundColor Cyan
