# Skrypt do uruchomienia JAKO ADMINISTRATOR
# Naprawia zadanie "TECH_modul briefing" aby nie pokazywało widocznego okna

# Sprawdzenie czy jest admin
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "BŁĄD: Uruchom ten skrypt JAKO ADMINISTRATOR!" -ForegroundColor Red
    Write-Host "Kliknij prawym przyciskiem na powershell.exe -> 'Uruchom jako administrator'"
    exit 1
}

$taskName = "TECH_modul briefing"

try {
    # Pobierz istniejące zadanie
    $task = Get-ScheduledTask -TaskName $taskName

    # Zmień akcję na PowerShell z ukrytym oknem
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\PythonProject\TECH_modul\tools\briefing_hidden.ps1"

    # Zastosuj zmianę
    Set-ScheduledTask -TaskName $taskName -Action $action

    Write-Host "✓ Naprawiono zadanie '$taskName'" -ForegroundColor Green
    Write-Host "  Okno PowerShell nie będzie się już pojawiać o 7:00 rano"
} catch {
    Write-Host "✗ Błąd: $_" -ForegroundColor Red
    exit 1
}
