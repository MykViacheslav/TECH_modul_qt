<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
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
=======
=======
>>>>>>> theirs
# MULTI COMPUTER SETUP (SAFE DEV-FIRST FLOW)

## Status check before cloning (computer #1)

Before configuring the second computer, verify:

- GitHub repository is reachable.
- Repository visibility is set to **private**.
- Latest required commit is pushed (example: `a565de5`).
- `.gitignore` protects sensitive/local artifacts:
  - `database/*.db`
  - `backups/`
  - `Faktury/`
  - `.venv/`
  - `node_modules/`
  - `.next/`
- `requirements.txt` is committed.
- This document exists in the repository.
=======
# MULTI COMPUTER SETUP (SAFE DEV-FIRST FLOW)

## Komputer #1 (biuro) — co zrobić najpierw

Na pierwszym komputerze przygotuj repozytorium tak, żeby drugi komputer mógł bezpiecznie zacząć pracę:

1. Sprawdź, że repo na GitHub istnieje i jest **private**.
2. Wypchnij aktualne zmiany do gałęzi roboczej.
3. Upewnij się, że `.gitignore` zawiera co najmniej:
   - `database/*.db`
   - `backups/`
   - `Faktury/`
   - `.venv/`
   - `node_modules/`
   - `.next/`
   - `.env`
4. Zacommituj i wypchnij pliki projektowe wymagane do startu:
   - `requirements.txt`
   - pliki frontendu (`package.json`, `package-lock.json`)
   - tę instrukcję `docs/MULTI_COMPUTER_SETUP.md`
5. (Opcjonalnie) Oznacz stabilny commit tagiem, np. `multi-pc-ready`.

### Szybka checklista (PowerShell/Git Bash)

```bash
git status
git remote -v
git branch --show-current
```

Jeśli wszystko jest gotowe:

```bash
git add .
=======
=======
>>>>>>> theirs
# MULTI COMPUTER SETUP (SAFE DEV-FIRST FLOW)

Ten dokument opisuje bezpieczny workflow pracy na **2 komputerach**:
- **Komputer #1 (biuro)** przygotowuje repozytorium,
- **Komputer #2 (dom)** startuje wyłącznie w trybie DEV.

---

## 1) Komputer #1 (biuro) — przygotowanie repo

### 1.1 Sprawdzenie stanu repo

```bash
git status
git remote -v
git branch --show-current
```

Upewnij się, że:
1. Repozytorium na GitHub istnieje i jest **private**.
2. Pracujesz na właściwej gałęzi.
3. Lokalnie nie ma przypadkowych zmian do wysłania.

### 1.2 Minimalne reguły `.gitignore`

W `.gitignore` muszą być co najmniej:

- `database/*.db`
- `backups/`
- `Faktury/`
- `.venv/`
- `node_modules/`
- `.next/`
- `.env`

### 1.3 Co commitować, a czego nie

✅ Commituj:
- kod źródłowy,
- `requirements.txt`,
- pliki frontendu (`package.json`, `package-lock.json`),
- dokumentację (`docs/`).

❌ Nie commituj:
- `database/*.db`,
- `backups/`,
- `Faktury/`,
- `.env`.

### 1.4 Bezpieczny push (bez `git add .`)

```bash
git add requirements.txt package.json package-lock.json docs/MULTI_COMPUTER_SETUP.md
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
git commit -m "chore: prepare repo for second computer"
git push
```

<<<<<<< ours
<<<<<<< ours
> Uwaga: jeśli masz lokalne dane firmowe (bazy, backupy, faktury), **nie dodawaj ich do commita**.
>>>>>>> theirs

## Computer #2 prerequisites (Windows)

Install:

1. Git for Windows
2. Python 3.10.x
3. Node.js LTS
4. (Optional) GitHub CLI
5. (Optional) PyCharm

## First-time clone on computer #2
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
=======
>>>>>>> theirs
> Jeśli commitujesz inne pliki, dodawaj je świadomie po nazwie.

---

## 2) Komputer #2 (dom) — instalacja i pierwszy start

### 2.1 Wymagania

Zainstaluj:
1. Git for Windows
2. Python 3.10.x
3. Node.js LTS
4. (Opcjonalnie) GitHub CLI
5. (Opcjonalnie) PyCharm

### 2.2 Klonowanie repo
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs

```powershell
cd C:\PythonProject
git clone https://github.com/MykViacheslav/TECH_modul_qt.git TECH_modul
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
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
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
cd C:\PythonProject\TECH_modul
```

## Backend environment (Python)

```powershell
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
=======
>>>>>>> theirs
cd C:\PythonProject\TECH_modul
```

### 2.3 Backend (Python)

```powershell
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
```

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
Sprawdz czy dziala:

```powershell
.\.venv\Scripts\python.exe --version
# Powinno pokazac: Python 3.10.x
```

---

## 4. Instalacja zaleznosci frontend
=======
## Frontend dependencies
>>>>>>> theirs
=======
## Frontend dependencies
>>>>>>> theirs
=======
## Frontend dependencies
>>>>>>> theirs
=======
### 2.4 Frontend (Node)
>>>>>>> theirs
=======
### 2.4 Frontend (Node)
>>>>>>> theirs

```powershell
cd C:\PythonProject\TECH_modul\frontend
npm install
```

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
---

## 5. Uruchomienie backend (tryb DEV)
=======
## Run in DEV mode (backend)
>>>>>>> theirs
=======
## Run in DEV mode (backend)
>>>>>>> theirs
=======
## Run in DEV mode (backend)
>>>>>>> theirs
=======
### 2.5 Start backendu w DEV
>>>>>>> theirs
=======
### 2.5 Start backendu w DEV
>>>>>>> theirs

```powershell
cd C:\PythonProject\TECH_modul
$env:TECH_MODUL_ENV="dev"
.\.venv\Scripts\python.exe -m uvicorn src.api.main_api:app --host 127.0.0.1 --port 8000
```

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
Backend bedzie dostepny pod: http://127.0.0.1:8000

Aplikacja GUI (PyQt):

```powershell
cd C:\PythonProject\TECH_modul
$env:TECH_MODUL_ENV="dev"
.\.venv\Scripts\python.exe src/app/main.py
```

---

## 6. Uruchomienie frontend
=======
## Run in DEV mode (frontend, second terminal)
>>>>>>> theirs
=======
## Run in DEV mode (frontend, second terminal)
>>>>>>> theirs
=======
## Run in DEV mode (frontend, second terminal)
>>>>>>> theirs
=======
### 2.6 Start frontendu w DEV (drugie okno)
>>>>>>> theirs
=======
### 2.6 Start frontendu w DEV (drugie okno)
>>>>>>> theirs

```powershell
cd C:\PythonProject\TECH_modul\frontend
npm run dev
```

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
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
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
## Important rule

On the second computer, always start from **DEV**, not production.

Do **not** copy these through GitHub:

=======
=======
>>>>>>> theirs
---

## 3) Najważniejsza zasada bezpieczeństwa

Na komputerze domowym zaczynasz od **DEV**, nie od produkcji.

Nie przenoś przez GitHub:
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
- `database/*.db`
- `backups/`
- `Faktury/`
- `.env`

<<<<<<< ours
<<<<<<< ours
If home access to real company data is required later, prefer VPN/Tailscale or remote desktop instead of copying production databases.

## Recommended next step

Run the full installation test on computer #2 using this checklist, then validate backend + frontend startup.
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
=======
>>>>>>> theirs
Jeśli potrzebujesz dostępu do realnych danych firmy z domu, użyj:
- VPN / Tailscale,
- albo zdalnego pulpitu.

---

## 4) Następny krok

Wykonaj pełny test instalacji na komputerze #2 według tej instrukcji i potwierdź:
1. backend startuje na `127.0.0.1:8000`,
2. frontend startuje poprawnie,
3. aplikacja działa end-to-end w trybie DEV.
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
