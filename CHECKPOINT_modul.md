# CHECKPOINT_modul

Data: 2026-04-12
Zakres: stabilizacja live zakladki `Modul` (runtime), bez przebudowy logiki.

## 1) Akceptowany runtime target
- Runtime file: `src/tabs/modul/tab_modul.py`
- Runtime class: `TabModul`
- Front content source: `src/tabs/modul/front_hardware_block.py`

## 2) Akceptowany balans splittera (STEP 43)
- Domyslne proporcje: `[210, 1080, 210]` (`left, center, right`)
- Cel: mocniejszy fokus na obszar rysunku (center), prawa strona ograniczona.

## 3) Akceptowana struktura lewego panelu
Lewa strefa pozostaje oparta o lokalne zakladki pionowe:
- Material
- Front
- Okucia
- Struktura
- BOM

Freeze po lokalnych cleanupach:
- `Okucia` -> sekcje kontekstowe
- `Struktura` -> sekcje kontekstowe
- `Material` -> sekcje (`Profil`, `Material i okleina`, `Baza cen`)
- `Front` -> usunieta duplikacja luzow top-level, dodana sekcja `Tryb i okucia`

## 4) Akceptowana struktura centrum
- Quick bar + pasek wymiarow
- Glowny canvas rysunku jako dominujacy obszar roboczy
- Bez zmian logiki renderu i obliczen

## 5) Akceptowana struktura prawego panelu
- Lekki panel techniczny z pionowymi zakladkami:
  - Podglad
  - Oklejanie
  - BOM i koszty
- Bez przebudowy logiki

## 6) Lekka ochrona regresji (freeze guard)
Dodany test:
- `tests/test_tab_modul_checkpoint_freeze.py`

Co pilnuje:
1. Domyslny balans splittera `[210, 1080, 210]`.
2. Zakladka `Front` nie ma juz duplikowanych wierszy luzow na top-level (`Luz lewy/prawy/gorny/dolny/miedzy frontami`), a ma sekcje `Luzy` i `Tryb i okucia`.

## 7) Jak uruchomic regresje
```bat
cd /d C:\PythonProject\TECH_modul
.\.venv\Scripts\python.exe -m pytest tests/test_tab_modul_checkpoint_freeze.py tests/test_front_hardware_front_zone.py -q
```

## 8) Jak uruchomic aplikacje
```bat
cd /d C:\PythonProject\TECH_modul
.\.venv\Scripts\python.exe src\app\main.py
```
