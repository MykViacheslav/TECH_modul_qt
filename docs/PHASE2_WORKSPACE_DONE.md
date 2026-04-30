# Phase 2 Workspace - Done

Data: 2026-04-26

## Cel Phase 2
Rozszerzenie wspolnego workspace shell o realny kontekst sciany i podstawowy kontekst rozmieszczenia modulow, bez przebudowy calego planera.

## Zrealizowany zakres
- Wspolna scena pokazuje realny kontekst sciany:
- granice sciany
- linie bazowa (floor baseline)
- etykiety wymiarow
- nazwe sciany
- Moduly sa renderowane w relacji do kontekstu sciany.
- Dodana podstawowa warstwa przeszkod (placeholdery) z danych sciany:
- pozycja
- rozmiar
- etykieta (nazwa/typ)
- Dodany minimalny payload placement dla modulow:
- `module_id`
- `wall_name`
- `komplet_id`
- `pos_x`, `pos_y`
- `width`, `height`, `depth`
- `display_label`
- `is_selected`
- Synchronizacja selekcji:
- scena -> drzewo
- drzewo -> scena
- scena/drzewo -> aktywny kontekst modulu
- Integracja z realna zakladka `Modul` pozostala aktywna (`Otworz aktywny modul`).
- Empty-state i fallbacki:
- brak scian
- brak kompletow
- komplet bez modulow
- komplet wskazuje nieistniejaca sciane

## Zachowane guardrails
- Brak duplikowania logiki edycji modulu.
- Brak przepisywania `TabModul` i `TabSciana`.
- Brak drugiego silnika sceny.
- Brak pelnego obstacle workflow i brak engine collision/snap/constraints.

## Zmienione pliki
- `src/tabs/plan/tab_plan.py`
- `tests/test_tab_plan_workspace_shell.py`
- `docs/PHASE2_WORKSPACE_DONE.md`

## Test/build status
- `python -m py_compile src\\tabs\\plan\\tab_plan.py tests\\test_tab_plan_workspace_shell.py` - OK
- `pytest -q tests/test_tab_plan_workspace_shell.py` - OK (5 passed)
- `pytest -q tests/test_tabs_registry_with_rysunek.py` - OK (1 passed)

## Definition of Done - status
- Shared workspace displays real wall context - DONE
- Modules are shown in relation to that wall - DONE
- Selection sync scene/tree/module context works - DONE
- Modes `Projekt/Sciana/Modul/Komplet` remain operational - DONE
- Active module can still be opened in real Modul tab - DONE
- Obstacle placeholders/basic objects can exist in the same scene - DONE
- No duplicate module logic introduced - DONE
- Tests pass and Phase 1 behavior remains stable - DONE

## Co czeka na Phase 3
- Pelny obstacle workflow
- Collision checking
- Snapping/auto-alignment
- Advanced komplet grouping
- Pelny edytor geometrii sciany
- Rich drag planner interactions
