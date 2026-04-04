$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectRoot "data\logs"
$StdOutLog = Join-Path $LogDir "pack_scanner_server.out.log"
$StdErrLog = Join-Path $LogDir "pack_scanner_server.err.log"
$HttpsPort = "9443"

if (!(Test-Path $PythonExe)) {
    throw "Nie znaleziono interpretera: $PythonExe"
}
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$alreadyRunning = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -match "python") -and
        (($_.CommandLine -like "*-m src.app.main*--server*") -or ($_.CommandLine -like "*src\app\main.py*--server*")) -and
        ($_.CommandLine -like "*--https*") -and
        ($_.CommandLine -like "*--https-port $HttpsPort*")
    } |
    Select-Object -First 1

if ($null -ne $alreadyRunning) {
    Write-Host "Serwer juz dziala (PID=$($alreadyRunning.ProcessId))."
    exit 0
}

$args = @(
    "-m", "src.app.main",
    "--server",
    "--https",
    "--https-port", $HttpsPort
)

$proc = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList $args `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdOutLog `
    -RedirectStandardError $StdErrLog `
    -PassThru

Write-Host "Uruchomiono serwer Pack Scanner (PID=$($proc.Id))."
