# Konfiguruje Windows Task Scheduler dla codziennego briefingu TECH_modul
# Uruchom jako Administrator: kliknij PPM na plik → "Uruchom jako administrator"

$TaskName   = "TECH_modul Briefing"
$BatFile    = "C:\PythonProject\TECH_modul\tools\briefing_start.bat"
$StartAt    = "07:00"

# Usuń stare zadanie jeśli istnieje
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Usunieto stare zadanie." -ForegroundColor Yellow
}

$Action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatFile`""
$Trigger = New-ScheduledTaskTrigger -Daily -At $StartAt
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -WakeToRun $false

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $Action `
    -Trigger  $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "  Zadanie '$TaskName' zostalo utworzone!" -ForegroundColor Green
Write-Host "  Uruchamia sie codziennie o $StartAt" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Mozesz je znalezc w: Harmonogram zadan -> '$TaskName'" -ForegroundColor Cyan
Write-Host "Aby uruchomic teraz: kliknij PPM -> 'Uruchom'" -ForegroundColor Cyan
Write-Host ""
pause
