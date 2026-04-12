# CHECKPOINT - Wycena Hub (Step 57)

Data: 2026-04-12  
Projekt root: `C:\PythonProject\TECH_modul`

## 1. Zaakceptowany runtime
- Glowna zakladka `Wycena` laduje klase:
  - `src/tabs/wycena_hub/tab_wycena_hub.py`
  - `TabWycenaHub`
- Rejestracja runtime:
  - `src/tabs/registry.py` (`build_tabs()` -> `"Wycena"` -> `TabWycenaHub`)

## 2. Zaakceptowana struktura podzakladek (6)
W hubie `Wycena` dziala 6 podzakladek:
1. `Wycena projektu`
2. `Szybka wycena`
3. `Import 3D`
4. `Uslugi`
5. `Rozkroj`
6. `Podsumowanie`

## 3. Zaakceptowany context-lock z Komplet
- Przeplyw:
  - `Komplet -> sig_open_wycena_requested`
  - `MainWindow._open_assembly_in_wycena(...)`
  - `TabWycenaHub.open_assembly_for_pricing(...)`
  - `TabWycena.open_assembly_for_pricing(...)`
- Zachowanie docelowe:
  - auto-przelaczenie na tryb `assemblies`
  - auto-ustawienie `order` zgodnie z incoming assembly
  - fokus na rekordzie konkretnego kompletu

## 4. Zaakceptowany cleanup tekstow (encoding/readability)
W `src/tabs/wycena/tab_wycena.py` utrzymujemy poprawne kluczowe etykiety, m.in.:
- `Tryb wyceny:`
- `Wycena wstepna`
- `Wartosc materialow`
- `Marza %`
- `Zamowienie`

Nie wracamy do uszkodzonych form mojibake.

## 5. Zaakceptowane rozroznienie trybow (mode banner)
W `src/tabs/wycena_hub/tab_wycena_hub.py` utrzymujemy aktywny banner trybu:
- dla `Wycena projektu`:
  - `TRYB SYSTEMOWY: WYCENA PROJEKTU`
- dla `Szybka wycena`:
  - `TRYB HANDLOWY: SZYBKA WYCENA`

Banner aktualizuje sie przy przelaczaniu podzakladek.

## 6. Zaakceptowany stan Rozkroj (Step 56)
- `Rozkroj` nie jest juz placeholderem.
- Podzakladka `Rozkroj` istnieje w hubie i laduje panel read-only.
- Panel pokazuje tylko dane z istniejacego `ProjectModel.giblab_result`:
  - `real_sheets_count`
  - `real_area_m2`
  - `scrap_m2`
  - `utilization_pct`
  - `difference_vs_theory`
- Dla braku danych dziala pusty stan:
  - komunikat o braku danych rozkroju dla biezacego projektu/importu
  - wskazowka, aby wczytac wynik GiB Lab w `Import 3D` (krok 5)

## 7. Lekka ochrona regresji
Plik freeze testow:
- `tests/test_wycena_checkpoint_freeze.py`

Zakres ochrony:
- runtime `Wycena` -> `TabWycenaHub`
- 6 podzakladek huba, w tym `Rozkroj`
- dzialanie mode banner dla 2 glownych trybow
- context-lock dla `open_assembly_for_pricing(...)`
- utrzymanie kluczowych tekstow
- `Rozkroj` nie jest placeholderem
- panel metryk i empty state dla `Rozkroj` istnieja

## 8. Jak uruchomic checki
```powershell
cd /d C:\PythonProject\TECH_modul
.\.venv\Scripts\python.exe -m pytest tests/test_wycena_checkpoint_freeze.py tests/test_wycena_hub_integration.py tests/test_wycena_tab.py -k "checkpoint or hub_has_six_subtabs or tab_registry_has_wycena_hub or mode_banner or rozkroj or open_assembly_locks_order_context" -q
```

## 9. Jak uruchomic aplikacje
```powershell
cd /d C:\PythonProject\TECH_modul
.\.venv\Scripts\python.exe src\app\main.py
```
