# 🔧 Naprawa: Powershell/CMD okna się otwierają

## Problem
Okno PowerShell/CMD pojawia się periodycznie, uniemożliwiając pracę.

## Przyczyny

### 1. **Zadanie "TECH_modul briefing" (7:00 AM)**
Uruchamia `cmd.exe /c briefing_start.bat` **bez ukrycia okna**.

**Objawy:**
- Okno CMD pojawia się codziennie o 7:00 rano
- Trwa kilka sekund

**Rozwiązanie:**
Uruchom jako ADMINISTRATOR:
```powershell
C:\PythonProject\TECH_modul\tools\fix_briefing_task_admin.ps1
```

---

## Kroki naprawy

### Krok 1: Testuj serwer
```powershell
# Uruchom w normalnym PowerShell (bez admin):
C:\PythonProject\TECH_modul\tools\test_server_startup.ps1
```

Sprawdź czy serwer:
- Uruchomił się bez błędów
- Ciągle się nie zawiesza/restartuje
- Słucha na porcie 9443

### Krok 2: Napraw zadanie briefing (ADMIN)
```powershell
# Uruchom jako ADMINISTRATOR (kliknij prawym -> Uruchom jako administrator)
C:\PythonProject\TECH_modul\tools\fix_briefing_task_admin.ps1
```

### Krok 3: Sprawdź logowanie
Jeśli dalej pojawia się okno, sprawdź logi:
```powershell
Get-EventLog -LogName Application -Newest 50 | Where-Object { $_.Source -like '*python*' -or $_.Message -like '*powershell*' }
```

---

## Jeśli dalej nie działa

### Czek listy:

**A) Czy serwer działa normalnie?**
```powershell
netstat -ano | findstr 9443
```
Powinna być linia z LISTENING na porcie 9443.

**B) Czy w Task Schedulerze są przeterminowane taski?**
```powershell
Get-ScheduledTask | Where-Object { $_.State -eq 'Disabled' }
```

**C) Czy są inne procesy spawdzające PowerShell?**
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*powershell*' -or $_.CommandLine -like '*cmd*' }
```

**D) Logi błędów**
Spraw dź pliki:
- `data/logs/pack_scanner_server.out.log`
- `data/logs/pack_scanner_server.err.log`

---

## Zmienione pliki

- `tools/briefing_hidden.ps1` — wrapper do run briefing bez okna
- `tools/briefing_hidden.vbs` — już istniał, używany przez BAT
- `tools/fix_briefing_task_admin.ps1` — skrypt do naprawy Task Schedulera

## Następnym razem

Po tym, jak naprawisz zadanie, okno CMD nie powinno się więcej pojawiać o 7:00 rano.

Jeśli pojawia się w inne godziny, to może być:
- Inna zaplanowana akcja
- Proces spawdzany ręcznie
- Błąd w pliku `.venv` lub konfiguracji

Napisz ile dokładnie razy dziennie to się dzieje i o jakich godzinach!

---

**Potrzebujesz help?**
Wyślij wiadomość: `Naprawa PowerShell - [opisz co się dzieje]`
