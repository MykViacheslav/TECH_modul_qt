# TECH_modul — Praca na dwoch komputerach (biuro + dom)

Repozytorium: `https://github.com/MykViacheslav/TECH_modul_qt.git` (prywatne)

---

## 1. Co zainstalowac na drugim komputerze

| Program | Wersja | Link |
|---------|--------|------|
| Git for Windows | najnowsza | https://git-scm.com/download/win |
| Python | **3.10.x** (zgodna z projektem) | https://www.python.org/downloads/ |
| Node.js | LTS (20.x lub 22.x) | https://nodejs.org/ |
| PowerShell | wbudowany w Windows | - |
| GitHub CLI (opcjonalnie) | najnowsza | https://cli.github.com/ |
| PyCharm (opcjonalnie) | Community / Professional | https://www.jetbrains.com/pycharm/ |

**Wazne przy instalacji Pythona:**
- Zaznacz "Add Python to PATH"
- Zaznacz "Install for all users"

---

## 2. Klonowanie projektu

Otworz PowerShell i wykonaj:

```powershell
cd C:\PythonProject
git clone https://github.com/MykViacheslav/TECH_modul_qt.git TECH_modul
cd TECH_modul
```

Jesli repozytorium jest prywatne, Git zapyta o dane logowania.
Mozesz uzyc GitHub CLI:

```powershell
gh auth login
gh repo clone MykViacheslav/TECH_modul_qt TECH_modul
```

---

## 3. Tworzenie srodowiska Python (venv)

```powershell
cd C:\PythonProject\TECH_modul
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
```

Sprawdz czy dziala:

```powershell
.\.venv\Scripts\python.exe --version
# Powinno pokazac: Python 3.10.x
```

---

## 4. Instalacja zaleznosci frontend

```powershell
cd C:\PythonProject\TECH_modul\frontend
npm install
```

---

## 5. Uruchomienie backend (tryb DEV)

```powershell
cd C:\PythonProject\TECH_modul
$env:TECH_MODUL_ENV="dev"
.\.venv\Scripts\python.exe -m uvicorn src.api.main_api:app --host 127.0.0.1 --port 8000
```

Backend bedzie dostepny pod: http://127.0.0.1:8000

Aplikacja GUI (PyQt):

```powershell
cd C:\PythonProject\TECH_modul
$env:TECH_MODUL_ENV="dev"
.\.venv\Scripts\python.exe src/app/main.py
```

---

## 6. Uruchomienie frontend

```powershell
cd C:\PythonProject\TECH_modul\frontend
npm run dev
```

Frontend bedzie dostepny pod: http://localhost:3000

---

## 7. Codzienna praca z Git

### Przed rozpoczeciem pracy (sciagnij zmiany):

```powershell
cd C:\PythonProject\TECH_modul
git pull
```

### Po zakonczeniu pracy (wyslij zmiany):

```powershell
cd C:\PythonProject\TECH_modul
git status
git add .
git commit -m "opis co zmieniono"
git push
```

### Jesli sa konflikty:

```powershell
git pull
# Rozwiaz konflikty w edytorze
git add .
git commit -m "resolve merge conflicts"
git push
```

---

## 8. WAZNA ZASADA BEZPIECZENSTWA — bazy danych

**NIGDY nie synchronizuj plikow baz danych (.db) przez GitHub!**

- Pliki `.db`, `.sqlite`, `.sqlite3` sa w `.gitignore` i NIE trafiaja do repozytorium
- Produkcyjna baza danych pozostaje TYLKO na komputerze w biurze (serwerze)
- Na komputerze domowym pracujesz na lokalnej bazie DEV
- Kopie zapasowe baz rob recznie, nie przez Git
- Folder `backups/` i `database/` sa ignorowane przez Git

### Co jest synchronizowane przez Git:
- Kod zrodlowy (Python, TypeScript, JavaScript)
- Konfiguracja projektu (package.json, .gitignore)
- Szablony (data_config.json.template)
- Dokumentacja
- Testy

### Co NIE jest synchronizowane:
- Bazy danych (*.db, *.sqlite)
- Srodowisko wirtualne (.venv/)
- node_modules/
- Logi (*.log)
- Sekrety (.env)
- Kopie zapasowe (backups/)

---

## 9. Dostep do produkcji z domu (zalecenie)

Jesli potrzebujesz dostepu do produkcyjnej bazy danych lub serwera z domu:

- **NIE kopiuj** produkcyjnej bazy miedzy komputerami
- Uzywaj jednego glownego serwera/komputera do produkcji
- Z domu laczcz sie przez:
  - **Pulpit zdalny** (Remote Desktop / AnyDesk / TeamViewer)
  - **VPN** (np. Tailscale — darmowy, prosty w konfiguracji)
- Na komputerze domowym pracuj TYLKO na bazie DEV

Ta konfiguracja chroni dane produkcyjne przed przypadkowym nadpisaniem lub utrata.

---

## 10. Rozwiazywanie problemow

### Git nie widzi zmian:
```powershell
git status
git diff
```

### Blad przy `pip install`:
```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\pip.exe install -r requirements.txt
```

### Blad przy `npm install`:
```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
```

### Sprawdzenie konfiguracji Git:
```powershell
git config user.name
git config user.email
```

Jesli puste, ustaw:
```powershell
git config --global user.name "Twoje Imie"
git config --global user.email "twoj@email.com"
```
