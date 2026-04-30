$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut("C:\Users\mykyt\Desktop\TECH MODUL WEB.lnk")
Write-Host "Target: $($lnk.TargetPath)"
Write-Host "Arguments: $($lnk.Arguments)"
Write-Host "WorkDir: $($lnk.WorkingDirectory)"
