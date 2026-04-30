$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $DesktopPath 'TECH MODUL WEB.lnk'

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = 'C:\PythonProject\TECH_modul\START_WEB.bat'
$Shortcut.WorkingDirectory = 'C:\PythonProject\TECH_modul'
$Shortcut.IconLocation = 'shell32.dll,21'
$Shortcut.Description = 'Uruchom TECH MODUL - wersja webowa'
$Shortcut.Save()

Write-Host "Skrot utworzony: $ShortcutPath"
