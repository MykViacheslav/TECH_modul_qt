Get-NetTCPConnection -LocalPort 8000, 5173 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { 
    Write-Host "Killing process $($_.OwningProcess) on port $($_.LocalPort)"
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue 
}

# Kill node processes
Write-Host "Killing node processes..."
taskkill /f /im node.exe /t 2>$null

# Try to release log files
Write-Host "Releasing log files..."
$files = @("frontend.log", "backend.log")
foreach ($f in $files) {
    if (Test-Path $f) {
        try {
            Remove-Item $f -Force -ErrorAction Stop
            Write-Host "Removed $f"
        } catch {
            Write-Host "Failed to remove $f"
        }
    }
}
