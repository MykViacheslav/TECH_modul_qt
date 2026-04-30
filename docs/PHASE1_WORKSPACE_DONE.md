# Phase 1 Workspace - Done

Data: 2026-04-26

## Zakres wdrozenia
- Jeden wspolny workspace shell w `TabPlan`.
- Staly srodek pod scene (QGraphicsView).
- Lewy panel kontekstowy.
- Przelacznik trybow:
- `Projekt`
- `Sciana`
- `Modul`
- `Komplet`

## Integracja z istniejacym Modulem
- Klik modulu na scenie wybiera aktywny modul.
- Lewy panel pokazuje dane wybranego modulu.
- Akcja `Otworz aktywny modul` przechodzi do realnej zakladki `Modul`.
- Ladowanie odbywa sie przez istniejace `load_module_from_store_name`.
- Nie duplikowano frontendowej logiki preview/apply.

## Minimalny context Sciana
- Wspolny context sciany i kompletu w tym samym workspace.
- Podstawowe dane sciany (nazwa, wymiary) widoczne w trybie `Sciana`.
- Miejsce przygotowane pod dalszy rozwoj.

## Minimalny context Komplet
- Prosta struktura: `Sciana -> Komplet -> Moduly`.
- Klik modulu w drzewie synchronizuje aktywny modul na scenie.
- Bez rich edytora kompletu.

## Empty-state i guardy UX
- Gdy brak kompletow: blokada wyboru kompletu + czytelny komunikat.
- Gdy komplet bez modulow: placeholdery na scenie i w drzewie.
- Auto-wybor pierwszego modulu przy dostepnych danych.

## Czego celowo nie ruszano
- Brak pelnego redesignu UI.
- Brak przepisywania logiki `TabModul` i `TabSciana`.
- Brak nowego osobnego silnika sceny.
- Brak funkcji z Phase 2 (constraints, obstacle workflow, advanced grouping).

## Zmienione pliki
- `src/tabs/plan/tab_plan.py`
- `tests/test_tab_plan_workspace_shell.py`
- `docs/PHASE1_WORKSPACE_DONE.md`

## Test/build status
- `python -m py_compile src\\tabs\\plan\\tab_plan.py tests\\test_tab_plan_workspace_shell.py` - OK
- `pytest -q tests/test_tab_plan_workspace_shell.py` - OK (2 passed)
- `pytest -q tests/test_tabs_registry_with_rysunek.py` - OK (1 passed)
