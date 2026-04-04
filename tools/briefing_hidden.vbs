
' Uruchamia dev_briefing.py bez widocznego okna i otwiera wynik w Notatniku
Dim oShell, sFSO, sProject, sPython, sScript, sOutput
Set oShell = CreateObject("WScript.Shell")
Set sFSO   = CreateObject("Scripting.FileSystemObject")

sProject = "C:\PythonProject\TECH_modul"
sPython  = sProject & "\.venv\Scripts\python.exe"
sScript  = sProject & "\tools\dev_briefing.py"
sOutput  = sProject & "\briefing.txt"

' Uruchom Python bez okna (0 = ukryte, True = czekaj)
oShell.Environment("Process")("PYTHONUTF8") = "1"
oShell.Run """" & sPython & """ """ & sScript & """", 0, True

' Otwórz Notatnik jeśli plik istnieje
If sFSO.FileExists(sOutput) Then
    oShell.Run "notepad """ & sOutput & """", 1, False
End If
