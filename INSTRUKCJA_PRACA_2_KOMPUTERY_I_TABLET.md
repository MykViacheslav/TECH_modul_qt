# TECH_modul - instrukcja pracy na 2 komputerach i tablecie

## 1. Cel

Ta instrukcja pokazuje:
- jak pracować nad programem na dwóch komputerach,
- jak bezpiecznie zapisywać zmiany,
- jak używać tabletu Android do rejestracji pracowników przez kiosk webowy,
- jak wrócić do poprzedniego stanu, jeśli coś pójdzie nie tak.

## 2. Najważniejsza zasada

Zawsze pracuj przez Git.

Nie kopiuj ręcznie całych folderów między komputerami, jeśli chcesz zachować porządek.
Najlepiej:
- komputer 1: praca i zapis zmian,
- GitHub: miejsce synchronizacji,
- komputer 2: `git pull` i dalsza praca.

## 3. Pierwsze uruchomienie na nowym komputerze

### 3.1. Pobranie projektu

```powershell
git clone <URL_REPOZYTORIUM_GITHUB>
cd TECH_modul
```

### 3.2. Utworzenie środowiska

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Jeśli w repo nie ma `requirements.txt`, zainstaluj zależności ręcznie według tego, co jest potrzebne w projekcie.

### 3.3. Uruchomienie aplikacji

```powershell
python .\src\app\main.py
```

## 4. Praca na dwóch komputerach

### 4.1. Komputer główny

Na komputerze, na którym normalnie pracujesz:

```powershell
git status
git add -A
git commit -m "opis zmian"
git push
```

### 4.2. Drugi komputer

Na drugim komputerze:

```powershell
git pull
```

Potem uruchamiasz program i pracujesz dalej.

### 4.3. Jeśli oba komputery zmieniają ten sam plik

Najlepiej:
1. dokończyć pracę na jednym komputerze,
2. zrobić commit i push,
3. na drugim komputerze wykonać `git pull`,
4. dopiero wtedy kontynuować.

To zmniejsza ryzyko konfliktów.

## 5. Bezpieczne punkty powrotu

Jeśli chcesz wrócić do znanego stanu:

```powershell
git checkout codex/snapshot-2026-03-27
```

Jeśli masz własny commit:

```powershell
git log --oneline
git checkout <HASH_COMMITU>
```

Jeśli potrzebujesz wrócić z powrotem do najnowszej gałęzi:

```powershell
git checkout main
```

## 6. Tablet Android - rejestracja pracowników

### 6.1. Jak działa kiosk

Tablet Android nie uruchamia tej aplikacji PyQt6 lokalnie.
Na tablecie otwierasz stronę web kiosku w Chrome.

Schemat:
- komputer w firmie uruchamia serwer TECH_modul,
- tablet Android otwiera stronę `kiosk`,
- pracownik skanuje QR albo wpisuje PIN,
- system zapisuje start, przerwę i koniec pracy.

### 6.2. Uruchomienie serwera

Na komputerze z bazą danych:

```powershell
C:\PythonProject\TECH_modul\.venv\Scripts\python.exe C:\PythonProject\TECH_modul\src\app\main.py --server --server-port 8000
```

### 6.3. Adres na tablecie

Na tablecie Android otwórz w Chrome:

```text
http://<IP_KOMPUTERA>:8000/kiosk
```

Przykład:

```text
http://192.168.1.50:8000/kiosk
```

### 6.4. Co pracownik robi na tablecie

Pracownik może:
- zeskanować QR,
- wpisać `worker_id`,
- wpisać awaryjny PIN,
- dotknąć przycisk:
  - `Start pracy`
  - `Przerwa start`
  - `Przerwa koniec`
  - `Koniec pracy`

### 6.5. Co musi mieć pracownik

Każdy pracownik powinien mieć:
- `worker_id`,
- `pin_code`,
- QR wydrukowany na karcie lub kartce,
- wpisany w bazie pracowników.

### 6.6. Gdzie zapisują się dane

Wpisy czasu pracy zapisują się do:
- `work_time.json`,
- `work_time_sessions.json` dla aktywnych sesji.

## 7. Jak wygenerować QR pracownika

W aplikacji:
1. Otwórz `Pracownicy`.
2. Wybierz pracownika.
3. Kliknij `Pokaż QR`.
4. Możesz też użyć:
   - `Zapisz PNG`,
   - `Eksport PDF`,
   - `Eksport do folderu`,
   - `Otwórz folder QR`.

Gotowe pliki lądują w:

```text
C:\PythonProject\TECH_modul\data\qr_workers
```

albo w folderze ustawionym przez `TECH_MODUL_DATA_DIR`.

## 8. Zalecany codzienny workflow

### Start dnia

1. Uruchom aplikację albo serwer.
2. Sprawdź `git pull`, jeśli pracujesz na więcej niż jednym komputerze.
3. Upewnij się, że tablet widzi kiosk.
4. Sprawdź, czy QR/PIN pracowników są aktualne.

### W trakcie pracy

1. Zmieniasz kod.
2. Testujesz lokalnie.
3. Robisz `git add -A`.
4. Robisz `git commit -m "..."`.
5. Robisz `git push`.

### Koniec dnia

1. Zapisz zmiany w Git.
2. Sprawdź, czy kiosk działa.
3. Jeśli trzeba, zrób PDF kart QR.

## 9. Rekomendacja organizacyjna

Najlepiej rozdzielić role:
- komputer 1: rozwój aplikacji,
- komputer 2: testy / uruchomienie w firmie,
- tablet: tylko rejestracja pracowników.

## 10. Minimalna zasada bezpieczeństwa

Nie pracuj jednocześnie na dwóch komputerach bez wcześniejszego `git pull`.

Jeśli nie jesteś pewien stanu:
1. zrób commit lokalnie,
2. sprawdź `git status`,
3. dopiero wtedy przełącz komputer.

## 11. Szybkie komendy

```powershell
git status
git add -A
git commit -m "opis zmian"
git push
git pull
git log --oneline
```

## 12. Autostart ekranu stanowiska w Windows

Jeśli chcesz, żeby po uruchomieniu komputera sam startował ekran stanowiska CNC:

1. Użyj pliku:
   - `C:\PythonProject\TECH_modul\START_STANOWISKO_CNC.bat`
   - `C:\PythonProject\TECH_modul\START_STANOWISKO_OKLEJANIE.bat`
   - `C:\PythonProject\TECH_modul\START_STANOWISKO_LAKIERNIA.bat`
   - `C:\PythonProject\TECH_modul\START_STANOWISKO_MONTAZ.bat`
   - `C:\PythonProject\TECH_modul\START_STANOWISKA_MENU.bat`
2. Kliknij prawym przyciskiem i utwórz skrót.
3. Otwórz folder autostartu Windows:
   - `Win + R`
   - wpisz `shell:startup`
4. Wklej tam skrót do `START_STANOWISKA_MENU.bat` albo do wybranego pliku `.bat`.

Po restarcie Windows uruchomi ekran:

```text
--wall --station cnc --station-only
```

Jeśli chcesz inny wydział, zrób drugi plik `.bat` z inną stacją:
- `oklejanie`
- `lakiernia`
- `montaz`

Jeśli chcesz jeden wspólny start:
- użyj `START_STANOWISKA_MENU.bat`
- wybierasz stację z menu
