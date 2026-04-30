# Phase 4 Workspace - Done

Data: 2026-04-26

## Cel etapu
Przeksztalcenie przeszkod z placeholderow w realny, podstawowy workflow obstacle w ramach wspolnego workspace.

## Co wdrozone
- Przeszkody jako obiekty pierwszej klasy na scenie (`obstacle_id`, `obstacle_type`, `pos_x_mm`, `pos_y_mm`, `width_mm`, `height_mm`, `label`, `is_selected`).
- Render i selekcja przeszkod na scenie.
- Kontekst Sciana rozszerzony o:
- liste przeszkod,
- filtr listy przeszkod (`Wszystkie` / `Tylko konfliktowe` / `Tylko krytyczne (H)`),
- priorytetyzacje listy przeszkod wg severity (H -> M -> brak),
- stabilne zasady selekcji: gdy filtr ukryje zaznaczona przeszkode, selekcja jest czyszczona i UI pozostaje spojne,
- szczegoly zaznaczonej przeszkody,
- czytelna liste modulow kolidujacych (nazwy/etykiety, nie tylko surowe identyfikatory),
- formularz edycji,
- akcje `Nowa`, `Dodaj`, `Aktualizuj`, `Usun`.
- Kontekst Modul i Komplet rozszerzony o czytelniejsza informacje o kolizjach z przeszkodami.
- Widocznosc warningow rozszerzona o poziomy `high/medium/none` w panelach i na scenie (oznaczenia etykiet przeszkod).
- Tryb Modul pokazuje teraz rozbicie konfliktow przeszkod wg typu (`Konflikty typy`), np. `door:1, column:1`.
- Akcja z poziomu Modulu: `Pokaz kolidujaca przeszkode` (przejscie do kontekstu Sciana z aktywna przeszkoda).
- Akcja z poziomu Sciany: `Pokaz kolidujacy modul` (przejscie do kontekstu Modul z aktywnym modulem).
- Cykliczne przechodzenie po konfliktach:
- `Sciana -> Modul` po wielu modulach kolidujacych z ta sama przeszkoda,
- `Modul -> Sciana` po wielu przeszkodach kolidujacych z tym samym modulem.
- Jawna akcja naprawcza `Napraw pozycje w scianie` dla przeszkod z `obstacle_out_of_wall`.
- Podstawowy workflow CRUD przeszkod (form-based) oparty o `WallStoreJson`.
- Ostrzezenia obstacle-specyficzne dla modulow:
- `obstacle_intersection_window`
- `obstacle_intersection_door`
- `obstacle_intersection_column`
- `obstacle_intersection_recess`
- `obstacle_intersection_pipe`
- `obstacle_intersection_utility`
- Payload konfliktu dla warningow:
- `warning_type`
- `obstacle_id`
- `obstacle_type`
- `module_id`
- `severity`
- `short_message`
- Relacje kolizji po stronie przeszkod:
- `intersecting_module_ids`
- `intersecting_module_count`
- Strefy ostrzegawcze przeszkod (`warning_zone_mm`, mapowane na `depth_mm`) dla lepszej detekcji konfliktow `utility/pipe`.
- Presety typu przeszkody (domyslne W/H/Z) dla szybszego tworzenia obiektow.
- Ostrzezenia przeszkod:
- `obstacle_invalid_size`
- `obstacle_out_of_wall`
- `overlapping_obstacles`
- Rozszerzone summary sciany:
- `obstacle_count`
- `obstacles_by_type`
- `blocking_obstacle_count`
- `intersecting_module_count`
- `obstacle_conflict_pairs_count`
- `obstacle_conflicts_by_type`
- `overlapping_obstacle_count`
- `obstacle_high_warning_count`
- `obstacle_medium_warning_count`
- `obstacle_out_of_wall_count`
- `obstacle_invalid_size_count`
- `module_high_warning_count`
- `module_medium_warning_count`

## Guardrails zachowane
- Brak przepisywania `TabModul` i `TabSciana`.
- Brak drugiego silnika sceny.
- Brak automatycznego auto-fix layoutu.
- Brak drag planner engine.

## Zmienione pliki
- `src/tabs/plan/tab_plan.py`
- `tests/test_tab_plan_workspace_shell.py`
- `docs/PHASE4_WORKSPACE_DONE.md`

## Test/build status
- `python -m py_compile src\\tabs\\plan\\tab_plan.py tests\\test_tab_plan_workspace_shell.py` - OK
- `pytest -q tests/test_tab_plan_workspace_shell.py` - OK (27 passed)
- `pytest -q tests/test_tabs_registry_with_rysunek.py` - OK (1 passed)
