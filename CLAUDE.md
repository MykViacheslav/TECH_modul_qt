# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the application

```bash
python src/app/main.py
```

Requires Python 3.10+ and PyQt6. Dependencies are in `.venv/`.

To activate the venv on Windows:
```bash
.venv\Scripts\activate
```

## Running tests

```bash
# All tests (note: test_tab_bazy.py currently has a broken import — skip it)
python -m pytest tests/ --ignore=tests/test_tab_bazy.py -q

# Single test file
python -m pytest tests/test_smoke.py -v

# Single test by name
python -m pytest tests/test_module_def_domain_fields.py::test_name -v
```

Tests use a real `QApplication` instance (PyQt6). Most tests instantiate widgets directly — no mocking of the Qt layer. The `conftest.py` only adds the project root to `sys.path`.

The `TECH_MODUL_DATA_DIR` environment variable overrides the default `data/` directory used by all JSON stores (useful in tests to avoid polluting real data).

## Architecture

### Layer structure

```
src/domain/      — pure Python dataclasses, no Qt, no I/O
src/storage/     — JSON persistence, one class per entity (e.g. ModuleStoreJson)
src/tabs/        — PyQt6 tab widgets, one subdirectory per tab
src/app/         — MainWindow + app_settings (theme, drawing config)
src/widgets/     — shared reusable Qt widgets
src/core/        — drawing rules (hinges, drawers, etc.) and canvas logic
```

### Navigation model

`MainWindow` does **not** use a single flat `QTabWidget`. Instead:
- A **left sidebar** (`QWidget#Sidebar`, 128px wide) holds 5 group buttons.
- A `QStackedWidget` to the right holds one `QTabWidget` per group.
- Groups are defined in `_GROUPS` at the top of `main_window.py`.
- All cross-tab navigation goes through `MainWindow._navigate_to_tab(title: str)`.
- `MainWindow._tabs_by_title` maps tab title → widget instance (used by `_wire_cross_tab_signals`).

Navigation groups:
| Group | Tabs |
|-------|------|
| Sprzedaż | Start, Nowe zamowienie, Wycena, Sekcje do wyceny |
| Projekt | Modul, Komplet, Sciana |
| Firma | Kalendarz, Czas pracy, Wydatki stale firmy, Wydatki zmienne, Pracownik |
| Bazy | Bazy, BAZA_modul, Baza materialu, Baza szybkich wycen |
| Inne | Plan, Schemat, Ustawienia |

### Data flow

1. **Domain models** (`src/domain/`) are pure dataclasses — `ModuleDef`, `AssemblyDef`, `WallDef`, `ClientDef`, `OrderDef`, `WorkerDef`, etc.
2. **Stores** (`src/storage/`) persist to `data/*.json`. Each store resolves its path via `TECH_MODUL_DATA_DIR` env var or falls back to `<repo-parent>/data/`.
3. **Tabs** read/write through stores and emit Qt signals to request navigation. They never navigate directly — they emit a signal (e.g. `sig_open_komplet_requested`) and `MainWindow` handles it.
4. **Cross-tab signals** are wired once in `MainWindow._wire_cross_tab_signals()`. Adding a new cross-tab action means: add a signal to the source tab, wire it in `_wire_cross_tab_signals`, add an `_open_*` method in `MainWindow`.

### Theme system

`app_settings.py` holds `DrawingSettings` (canvas colors, grid) and `UiThemeSettings` (mode: day/night, motif: cream/blue/gray/green). Both are persisted in `data/settings.json`. The entire app stylesheet is regenerated and reapplied via `_apply_accessible_ui_scale()` whenever the theme changes.

### Module resolution

`ModuleDef` is the raw definition (dimensions, parts, materials). `ResolvedModuleDef` is the computed result after applying material profiles, edgeband overrides, and family rules. The resolution pipeline lives in `src/domain/module_resolution_service.py` and `assembly_resolution_service.py`.

### Adding a new tab

1. Create `src/tabs/<name>/tab_<name>.py` with a `QWidget` subclass.
2. Import and add it to `build_tabs()` in `src/tabs/registry.py`.
3. Add the tab title to the appropriate group in `_GROUPS` in `src/app/main_window.py`.
