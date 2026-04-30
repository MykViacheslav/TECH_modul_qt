# WEB WORKSPACE MODUL SCIANA KOMPLET PHASE 1 IMPLEMENTATION PLAN

## 1. Cel
Zrobic jeden wspolny workspace dla Modulu, Sciany i Kompletu, bez przeskakiwania miedzy rozlaczonymi ekranami, przy zachowaniu realnego modelu produkcyjnego jako zrodla prawdy.

## 2. Zakres Phase 1 (strict)
- Wspolna nawigacja i kontekst dla 3 obszarow.
- Synchronizacja selekcji (lista <-> scena <-> edytor).
- Ujednolicony model stanu po stronie web (workspace state).
- Reuzycie obecnych endpointow API (bez przebudowy domeny produkcyjnej).
- Minimalne brakujace endpointy pomocnicze tylko gdy konieczne.

Poza zakresem:
- Nowy silnik 3D/CAD.
- Pelna przebudowa plannera i wszystkich modułow aplikacji.
- Zaawansowany solver kolizji i automatyczny routing.

## 3. Stan obecny (fakty)
- `configuration/page.tsx`: Modul editor (operacje module preview/apply), realne API.
- `wall/page.tsx`: Sciana point-tool (wall preview/apply), realne API.
- `assembly/page.tsx`: Komplet-like bulk module operations + assembly summary.
- Dane modulu trwale w SQLite (`project_modules`, `spec_json`).
- Dane przeszkod/sciany czesciowo splitowane (JSON obstacles + osobne wall points).

## 4. Docelowy efekt po Phase 1
Uzytkownik otwiera jeden ekran workspace, wybiera projekt i:
1. Ustawia/edytuje sciane oraz punkty/przeszkody.
2. Wstawia i edytuje moduly w tym samym kontekście.
3. Grupuje moduly jako komplet (bulk + summary).
4. Widzi podsumowania (assembly/wall/workspace) bez zmiany strony.

## 5. Architektura UI (minimalna)
- Jedna strona shell: `frontend/src/app/workspace/page.tsx` jako host.
- Lewy panel trybow: `Project | Sciana | Modul | Komplet`.
- Srodkowy obszar: wspolna scena/lista (na start 2D/list-based, bez nowego renderera).
- Prawy panel: contextual editor aktywnego obiektu.

## 6. Architektura danych
Wprowadzic lokalny `WorkspaceState` (frontend) spinajacy:
- `projectId`, `activeMode`, `selectedWallId|Name`, `selectedModuleId`, `selectedGroupId`.
- cache: modules, wall points/obstacles, assembly summary, wall summary, workspace summary.
- dirty flags: `moduleDirty`, `wallDirty`, `kompletDirty`.

Source of truth zostaje backend + obecne endpointy operacji.

## 7. Integracja API (Phase 1)
Reuzycie istniejacych:
- `/config/modules/{project_id}`
- `/config/wall/{project_id}`
- `/projects/{project_id}/assembly-summary`
- `/projects/{project_id}/wall-summary`
- `/operations/module/preview|apply`
- `/operations/module/bulk/preview|apply`
- `/operations/wall/preview|apply`
- `/wall/{wall_name}`

Minimalny dodatek (tylko jesli braknie):
- jeden endpoint `workspace snapshot` agregujacy summary + counts, aby ograniczyc fetch chattiness.

## 8. Kolejnosc wdrozenia
1. Workspace shell + mode switch + wspolny project context.
2. Podpiecie Modulu do shella (bez zmiany logiki operacji).
3. Podpiecie Sciany do shella (preview/apply w tym samym kontekscie).
4. Podpiecie Kompletu (bulk operations + assembly summary).
5. Synchronizacja selekcji i podswietlenia miedzy sekcjami.
6. Save/reload + smoke testy reczne.

## 9. Kryteria odbioru Phase 1
- Jeden ekran workspace obsluguje Modul + Sciana + Komplet.
- Brak utraty danych przy przelaczaniu trybow.
- Operacje preview/apply dla modulu i sciany dzialaja jak przedtem.
- Komplet (bulk) dziala w tym samym kontekscie projektu.
- Summary aktualizuje sie po zmianach.

## 10. Ryzyka i mitigacje
- Split persistence (wall JSON vs module SQL):
  - Mitigacja: w Phase 1 nie migrowac, tylko jasno oznaczyc adaptery i kontrakty.
- Niespojnosc selekcji miedzy widokami:
  - Mitigacja: jeden centralny `WorkspaceState` + strict event flow.
- Regression w obecnych flow:
  - Mitigacja: reuzycie endpointow + testy smoke dla kazdego trybu.

## 11. Co potem (Phase 2)
- Glebsze powiazanie wall geometry -> placement constraints.
- Real komplet entity lifecycle (nie tylko bulk view).
- Ujednolicenie persistence dla sciany/przeszkod/modulow.
