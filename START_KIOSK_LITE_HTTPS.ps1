$ErrorActionPreference = 'Stop'

$root = 'C:\PythonProject\TECH_modul'
$python = Join-Path $root '.venv\Scripts\python.exe'
$main = Join-Path $root 'src\app\main.py'
$port = 8443

Set-Location $root

try {
    $client = New-Object System.Net.Sockets.TcpClient
    $alreadyRunning = $client.ConnectAsync('127.0.0.1', $port).Wait(700)
    $client.Close()
} catch {
    $alreadyRunning = $false
}

if (-not $alreadyRunning) {
    Start-Process -FilePath $python -ArgumentList @(
        $main,
        '--server',
        '--https',
        '--https-port',
        $port
    ) -WindowStyle Minimized | Out-Null

    $deadline = (Get-Date).AddSeconds(25)
    while ((Get-Date) -lt $deadline) {
        try {
            $probe = New-Object System.Net.Sockets.TcpClient
            $probe.Connect('127.0.0.1', $port)
            $probe.Close()
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
}

Start-Process 'https://127.0.0.1:8443/kiosk-lite'
