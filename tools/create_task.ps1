$TaskName = "TECH_modul Briefing"
$BatFile  = "C:\PythonProject\TECH_modul\tools\briefing_start.bat"

$Action   = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatFile`""
$Trigger  = New-ScheduledTaskTrigger -Daily -At "07:00"
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force
Write-Host "GOTOWE - zadanie '$TaskName' uruchamia sie codziennie o 07:00"
