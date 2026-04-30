Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*frontend.log*" } | Select-Object ProcessId, CommandLine
