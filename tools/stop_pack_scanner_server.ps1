$ErrorActionPreference = "Stop"
$HttpsPort = "9443"

$candidates = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -match "python") -and
        (($_.CommandLine -like "*-m src.app.main*--server*") -or ($_.CommandLine -like "*src\app\main.py*--server*")) -and
        ($_.CommandLine -like "*--https*") -and
        ($_.CommandLine -like "*--https-port $HttpsPort*")
    }

if ($null -eq $candidates -or $candidates.Count -eq 0) {
    Write-Host "Serwer Pack Scanner nie jest uruchomiony."
    exit 0
}

foreach ($proc in $candidates) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        Write-Host "Zatrzymano PID=$($proc.ProcessId)"
    } catch {
        Write-Warning "Nie udalo sie zatrzymac PID=$($proc.ProcessId): $($_.Exception.Message)"
    }
}
