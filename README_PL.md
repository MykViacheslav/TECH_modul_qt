# TECH_modul (start od zera)

## 1) Setup venv + biblioteki
PowerShell:
- `.\tools\setup_venv.ps1`

## 2) Testy + start aplikacji
- `.\tools\after_patch.ps1`

## Struktura
- `src/app` – aplikacja (MainWindow)
- `src/tabs/modul` – zakładka "Moduł"
- `src/ui` – komponenty UI (np. bloki zwijane)
- `src/domain` – modele domenowe (ModuleDef, PartDef)
- `src/storage` – pamięć stała (na razie JSON)
- `data/modules.json` – baza modułów