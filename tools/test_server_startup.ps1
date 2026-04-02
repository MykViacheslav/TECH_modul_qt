$ProjectRoot = 'C:\PythonProject\TECH_modul'
$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$LogFile = Join-Path $ProjectRoot 'data\logs\test_server.log'

Write-Host 'Test uruchomienia serwera...' -ForegroundColor Cyan
Write-Host ""

# Kill any existing server
Get-CimInstance Win32_Process | Where-Object {
    ($_.CommandLine -like '*--server*') -and ($_.CommandLine -like '*--https*')
} | ForEach-Object {
    Write-Host "Zatrzymuję istniejący serwer (PID=$($_.ProcessId))..."
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1

# Start server with logging
Write-Host 'Uruchamiam nowy serwer...'
$proc = Start-Process $PythonExe -ArgumentList @('-m', 'src.app.main', '--server', '--https', '--https-port', '9443') `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError ($LogFile + '.err') `
    -PassThru

Write-Host "Proces ID: $($proc.Id)"
Write-Host "Czekam 5 sekund na stabilizację..."
Start-Sleep -Seconds 5

# Check if still running
$check = Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue

if ($check) {
    Write-Host ""
    Write-Host "✓ SERWER JEST URUCHOMIONY!" -ForegroundColor Green
    Write-Host "  Adres: https://192.168.x.x:9443"
    Write-Host "  Port: 9443 (HTTPS)"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ SERWER ZMYKA SIĘ!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Standard Output:"
    if (Test-Path $LogFile) {
        Get-Content $LogFile -Tail 20
    }
    Write-Host ""
    Write-Host "Standard Error:"
    if (Test-Path ($LogFile + '.err')) {
        Get-Content ($LogFile + '.err') -Tail 20
    }
}
