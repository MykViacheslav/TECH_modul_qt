# TECH_modul - szybki start dla biura i kiosku

## 1. Start programu

Uruchom:

```powershell
C:\PythonProject\TECH_modul\START_STANOWISKA_MENU.bat
```

Z menu wybierz:
- `CNC`
- `Oklejanie`
- `Lakiernia`
- `Montaż`
- `Wszystkie stanowiska`

## 2. Start automatyczny

Jeśli chcesz, żeby kiosk startował sam po uruchomieniu Windows:

1. Kliknij prawym na `START_STANOWISKA_MENU.bat`.
2. Utwórz skrót.
3. `Win + R`
4. Wpisz `shell:startup`
5. Wklej tam skrót.

## 3. Tablet Android

Na tablecie otwórz:

```text
http://<IP_KOMPUTERA>:8000/kiosk
```

Pracownik może:
- zeskanować QR,
- wpisać PIN,
- nacisnąć `Start pracy`,
- nacisnąć `Przerwa start`,
- nacisnąć `Przerwa koniec`,
- nacisnąć `Koniec pracy`.

## 4. Karty QR pracowników

W aplikacji:
1. Wejdź w `Pracownicy`.
2. Wybierz pracownika.
3. Kliknij `Pokaż QR`.
4. Kliknij `Eksport PDF` albo `Eksport do folderu`.

Pliki QR zapisują się do:

```text
C:\PythonProject\TECH_modul\data\qr_workers
```

## 5. Zapis czasu pracy

Godziny pracy zapisują się do:
- `work_time.json`
- `work_time_sessions.json`

## 6. Krótkie komendy Git

```powershell
git status
git add -A
git commit -m "opis zmian"
git push
git pull
```



## 7. Kamera QR na tablecie

Jesli chcesz skanowac kamera tabletu, uruchom serwer tak:

```powershell
C:\PythonProject\TECH_modul\START_KIOSK_HTTPS.bat
```

Jesli chcesz lekki widok tylko QR + Start/Koniec:

```powershell
C:\PythonProject\TECH_modul\START_KIOSK_LITE_HTTPS.bat
```

Potem na tablecie otworz:

```text
https://<IP_KOMPUTERA>:8443/kiosk
```

Wersja lekka dziala pod:

```text
https://<IP_KOMPUTERA>:8443/kiosk-lite
```

Pierwszy raz trzeba zainstalowac certyfikat CA z folderu:

```text
C:\PythonProject\TECH_modul\data\https\TECH_modul_CA.crt
```

Jesli certyfikat nie jest zaufany, Chrome zablokuje kamere.
