# Manual Test Scenario: Complete Wycena Hub (6 Sub-tabs)

**Objective**: Verify full Wycena hub functionality including Usługi visibility in final summary and Polish UI text correctness.

**Setup**: Run `python src/app/main.py` with test data available.

---

## Phase 1: Navigation & Tab Discovery

### Test 1.1: Hub Access from Main Window
- [ ] Open app and navigate to "Sprzedaż" group in left sidebar
- [ ] Verify "Wycena" tab is visible and clickable
- [ ] Click "Wycena" tab → hub window loads
- [ ] Verify sub-tabs bar appears with 6 tabs

### Test 1.2: Sub-tab Verification
Verify all 6 tabs are present and labeled correctly:
- [ ] **Wycena projektu** — tab icon/label visible
- [ ] **Szybka wycena** — tab icon/label visible
- [ ] **Import 3D** — tab icon/label visible
- [ ] **Usługi** — tab icon/label visible (CRITICAL)
- [ ] **Rozkrój** — tab icon/label visible (placeholder)
- [ ] **Podsumowanie** — tab icon/label visible (CRITICAL)

### Test 1.3: Tab Switching
- [ ] Click each tab in sequence (order: Wycena, Szybka, Import, Usługi, Rozkrój, Podsumowanie)
- [ ] Verify no crashes or layout breaks
- [ ] Verify content changes appropriately for each tab
- [ ] Return to Podsumowanie (should be last in sequence)

---

## Phase 2: Usługi Tab Functionality

### Test 2.1: Usługi Tab Content Structure
Navigate to **Usługi** sub-tab:
- [ ] Verify 4 internal panels are visible (tabs or collapsible sections):
  - [ ] **Cennik** — service definitions table with columns: ID, Nazwa, Rodzaj, j.m, Cena [zł], Uwagi
  - [ ] **Klienci** — client list management
  - [ ] **Nowa usługa** — form to create new service entry
  - [ ] **Baza usług** — archive/reference section

### Test 2.2: Polish Text in Usługi Panels
Verify correct Polish text throughout:
- [ ] Cennik panel: "Wczytaj domyślny" button (NOT "domyslny")
- [ ] Cennik panel: "- Usuń wpis" button (NOT "Usun wpis")
- [ ] Klienci panel: "- Usuń klienta" button (NOT "Usun klienta")
- [ ] Nowa usługa panel: "- Usuń pozycje" button (NOT "Usun pozycje")
- [ ] Nowa usługa panel: "- Usuń formatke" button (NOT "Usun formatke")
- [ ] All text: "Klient:" label (NOT "Klijent:")
- [ ] All text: "[wybierz klienta]" placeholder (NOT "klijenta")
- [ ] All text: "Odśwież" button (NOT "Odswiez") — 2 occurrences expected
- [ ] All text: "Spis materiału:" label (NOT "materialu:")
- [ ] Table header: "Klient" column (NOT "Klijent")

### Test 2.3: Usługi Data Management
- [ ] Add a test service in "Nowa usługa" section
- [ ] Verify service appears in Cennik table
- [ ] Click "Odśwież" button → list updates
- [ ] Attempt to delete service → "- Usuń pozycje" works
- [ ] Verify no error dialogs or crashes

---

## Phase 3: Podsumowanie (Summary) Panel - Usługi Visibility

### Test 3.1: Summary Panel Structure
Navigate to **Podsumowanie** sub-tab:
- [ ] Panel loads without errors
- [ ] Financial breakdown grid is visible with 9 fields

### Test 3.2: Verify Usługi in Summary (CRITICAL)
The summary panel has 4 display modes based on data source:
- [ ] **Mode 1 (Quick Pricing)**: If user switches from "Szybka wycena" to Podsumowanie
  - [ ] Verify "Usługi dodatkowe" field appears in grid (row ~4, col 2)
  - [ ] Field shows value or "0.00 zł" if no services used

- [ ] **Mode 2 (Assemblies)**: If user switches from "Wycena projektu" to Podsumowanie
  - [ ] Verify "Usługi dodatkowe" field appears in grid
  - [ ] Field reflects any services added to assemblies

- [ ] **Mode 3 (Import 3D)**: If user switches from "Import 3D" to Podsumowanie
  - [ ] Verify "Usługi dodatkowe" field appears in grid
  - [ ] Field shows imported service values or "0.00 zł"

- [ ] **Mode 4 (Services)**: If user switches from "Usługi" to Podsumowanie
  - [ ] Verify **Usługi** mode displays full report text: *"Usługi są częścią końcowej wyceny"*
  - [ ] Verify this text appears in info/status area of summary
  - [ ] Verify table shows columns: Nazwa usługi, j.m, Ilość, Cena jm, Razem

### Test 3.3: Services Financial Integration
- [ ] Create or modify a service entry in "Usługi" tab
- [ ] Switch to Podsumowanie sub-tab → summary updates
- [ ] Verify service cost is reflected in "Usługi dodatkowe" field
- [ ] Verify grand total ("RAZEM") includes services
- [ ] Return to "Usługi" tab, modify service amount
- [ ] Switch back to Podsumowanie → verify change propagates

---

## Phase 4: Cross-tab Navigation & Data Persistence

### Test 4.1: Quick Pricing Flow
- [ ] Start in "Szybka wycena" tab
- [ ] Enter test data (assembly name, quantity, price)
- [ ] Add a service via "+" button or inline
- [ ] Switch to Podsumowanie → verify data persists
- [ ] Switch back to "Szybka wycena" → verify data unchanged

### Test 4.2: Assembly Pricing Flow
- [ ] Start in "Wycena projektu" tab
- [ ] Create/select an assembly
- [ ] Add Usługi to assembly (if UI supports it)
- [ ] Switch to Podsumowanie → verify summary updates
- [ ] Verify "Usługi dodatkowe" is non-zero (if services added)

### Test 4.3: Import 3D Flow
- [ ] Start in "Import 3D" tab
- [ ] Attempt to import a test .project file
- [ ] If successful, verify services are recognized
- [ ] Switch to Podsumowanie → verify summary shows imported data
- [ ] Verify "Usługi dodatkowe" field is populated correctly

### Test 4.4: Services-First Flow
- [ ] Start in "Usługi" tab
- [ ] Create a new service definition in Cennik
- [ ] Add the service to active quote (if UI supports it)
- [ ] Switch to Podsumowanie → verify service appears in summary
- [ ] Verify "Usługi są częścią końcowej wyceny" message displays

---

## Phase 5: Regression & Edge Cases

### Test 5.1: Empty State
- [ ] Load hub with empty/blank quote data
- [ ] Verify Podsumowanie shows all fields as "0.00 zł" or empty
- [ ] Verify no crashes or missing widgets
- [ ] Verify "Usługi dodatkowe" field appears even when empty

### Test 5.2: Large Data
- [ ] Create a quote with:
  - [ ] 5+ assemblies
  - [ ] 10+ services
  - [ ] Mixed pricing (material + labor + services)
- [ ] Verify Podsumowanie calculates correctly
- [ ] Verify no UI performance issues (lag, freezing)
- [ ] Verify "RAZEM" grand total is correct

### Test 5.3: UI Polish & Typography
- [ ] Scan all visible text for spelling/diacritical marks
- [ ] Verify all Polish characters render correctly (ą, ć, ę, ł, ń, ó, ś, ź, ż)
- [ ] Verify button labels are readable and centered
- [ ] Verify table column headers are aligned

### Test 5.4: Error Handling
- [ ] Attempt to delete all services → verify app doesn't crash
- [ ] Attempt to load invalid .project file in "Import 3D" → verify graceful error
- [ ] Try to save quote with invalid data → verify validation feedback
- [ ] Switch tabs rapidly → verify no race conditions

---

## Phase 6: Baza usług Tab (New Entry Point)

### Test 6.1: Navigate to Baza usług
- [ ] From main window, go to "Bazy" group
- [ ] Click "Baza usług" tab
- [ ] Verify layout matches Usługi → Cennik panel (same definitions, different context)
- [ ] Verify subtitle text: *"Aby użyć usługi w ofercie — przejdź do Wycena → Usługi"*

### Test 6.2: Service Definitions Sync
- [ ] Add a new service definition in "Baza usług"
- [ ] Navigate to Wycena → Usługi tab
- [ ] Verify new service appears in Cennik panel (cross-tab sync)
- [ ] Modify service price in "Baza usług"
- [ ] Return to Wycena → Usługi → verify price updated

---

## Acceptance Criteria

**All Phase tests must PASS**:
- ✓ All 6 tabs load without errors
- ✓ Tab switching is smooth and data persists
- ✓ Usługi tab has 4 sub-panels with correct Polish text (all 12 spelling fixes verified)
- ✓ Podsumowanie correctly displays "Usługi dodatkowe" in financial breakdown (all 4 modes)
- ✓ Podsumowanie displays *"Usługi są częścią końcowej wyceny"* message in services mode
- ✓ Services cost propagates to final summary/RAZEM calculation
- ✓ No crashes, layout breaks, or missing widgets
- ✓ No regression in existing tabs (Wycena projektu, Szybka wycena, Import 3D)

**Sign-off**: User confirms visual inspection of all flows and Polish text is correct.

---

## Notes

- **Wycena hub** is located in: `src/tabs/wycena_hub/tab_wycena_hub.py` (_SummaryPanel at lines 36-193)
- **Usługi tab** source: `src/tabs/uslugi/tab_uslugi.py` (Polish fixes applied to lines 616, 618, 224, 741, 894, 936, 743, 1891, 1194, 1567, 1897)
- **Baza usług** entry point: `src/tabs/baza_uslug/tab_baza_uslug.py` (new, wraps Cennik panel)
- **Permission mapping**: `src/domain/permissions.py` — "Baza uslug" has VIEW_SERVICES + VIEW_PRICING
- **Navigation groups**: `src/app/navigation_groups.py` — Usługi removed from Firma group, now only in Wycena hub and Bazy (as Baza usług)
