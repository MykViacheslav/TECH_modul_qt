# Phase 3 Workspace - Done

Data: 2026-04-26

## Cel etapu
Przejscie ze sceny pasywnej do podstawowego workspace layout, gdzie modul ma znaczenie pozycyjne i kolejnosciowe na scianie.

## Co wdrozone
- Podstawowe sterowanie layoutem (bez drag engine):
- `Przesun w kolejnosci <-`
- `Przesun w kolejnosci ->`
- `Wyrownaj do startu`
- `Wyrownaj do konca`
- `Uloz sekwencyjnie`
- `Zastosuj pozycje` (manualne `pos_x` + `spacing_after_mm`)
- Deterministyczna kolejnosc modulow (`sequence_index`) utrzymywana w payloadzie sceny.
- Podstawowe pola placement payload:
- `module_id`
- `wall_name`
- `komplet_id`
- `pos_x`, `pos_y`
- `width`, `height`, `depth`
- `occupied_width_mm`
- `display_label`
- `sequence_index`
- `warning_flags`
- `is_selected`
- Summary wykorzystania sciany:
- `wall_width_mm`
- `occupied_width_mm`
- `free_width_mm`
- `module_count`
- liczniki warningow
- Warning model (wykrywanie):
- `out_of_wall_left`
- `out_of_wall_right`
- `module_overlap`
- `obstacle_intersection`
- `missing_wall_reference`
- `invalid_layout_order`
- Synchronizacja selekcji pozostaje stabilna:
- scena -> drzewo
- drzewo -> scena
- scena/drzewo -> aktywny kontekst modulu
- Konteksty panelu zostaly rozbudowane:
- `Sciana`: wymiary + zajete/wolne + przeszkody
- `Modul`: pozycja, kolejnosc, warningi
- `Komplet`: liczba modulow + zajete/wolne + warning count

## Guardrails zachowane
- Brak duplikacji logiki edycji modulu (realna edycja nadal w `TabModul`).
- Brak przepisywania `TabSciana`.
- Brak drugiego silnika sceny.
- Brak automatycznego collision solving / snapping.

## Zmienione pliki
- `src/tabs/plan/tab_plan.py`
- `tests/test_tab_plan_workspace_shell.py`
- `docs/PHASE3_WORKSPACE_DONE.md`

## Test/build status
- `python -m py_compile src\\tabs\\plan\\tab_plan.py tests\\test_tab_plan_workspace_shell.py` - OK
- `pytest -q tests/test_tab_plan_workspace_shell.py` - OK (9 passed)
- `pytest -q tests/test_tabs_registry_with_rysunek.py` - OK (1 passed)
