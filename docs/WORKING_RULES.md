# Zasady Pracy z Systemem (Safe Work Mode - Phase 1)

Ten dokument określa zasady bezpiecznej pracy z bazą danych i kodem TECH_modul, mające na celu ochronę danych produkcyjnych.

## 1. Tryby Pracy (Environments)

System automatycznie wybiera bazę danych na podstawie zmiennej środowiskowej `TECH_MODUL_ENV`:

- **PRODUKCJA (`prod`)**: 
    - Uruchamianie: `set TECH_MODUL_ENV=prod` przed startem.
    - Plik: `database/tech_modul_prod.db`.
    - Zabezpieczenie: Przy każdym starcie/inicjalizacji system tworzy kopię zapasową w `backups/before_migration/`.
- **DEVELOPMENT (`dev`)**:
    - Uruchamianie: `set TECH_MODUL_ENV=dev` (domyślny).
    - Plik: `database/tech_modul_dev.db`.
    - Służy do testowania nowych funkcji na danych testowych.
- **TESTY (`test`)**:
    - Uruchamianie: Przez `pytest`.
    - Plik: `database/tech_modul_test.db`.
    - Zabezpieczenie: Testy mają całkowity zakaz dotykania pliku produkcyjnego.

## 2. Krytyczne Zakazy ("Czego nie wolno robić")

1. **NIE usuwaj ręcznie** pliku `database/tech_modul_prod.db` bez posiadania sprawdzonej kopii zewnętrznej.
2. **NIE edytuj bazy produkcyjnej** bezpośrednio przez narzędzia zewnętrzne (np. SQLite Browser), gdy aplikacja jest uruchomiona.
3. **NIE wyłączaj** mechanizmu `safe_mode` w kodzie (klasa `Database` musi zawsze z niego korzystać).
4. **NIE wykonuj operacji `DROP TABLE`** ani `TRUNCATE` na produkcji bez ustawienia dodatkowej flagi potwierdzającej: `set TECH_MODUL_PROD_CONFIRM=I_UNDERSTAND`.

## 3. Procedura Aktualizacji (Migracji)

Jeśli planujesz zmiany w strukturze bazy danych:
1. Przetestuj migrację w trybie `dev`.
2. Upewnij się, że testy `pytest` przechodzą.
3. Na produkcji: uruchom skrypt backupu `python scripts/backup_data.py`.
4. Dopiero potem uruchom nową wersję kodu.

## 4. Kopie Zapasowe (Backups)

- Backup automatyczny: `backups/before_migration/` (tylko przed zmianami schematu).
- Backup ręczny/pełny: `python scripts/backup_data.py` -> tworzy paczkę w katalogu `data_backups/`.
- Zaleca się kopiowanie folderu `data_backups/` na zewnętrzny nośnik raz w tygodniu.
