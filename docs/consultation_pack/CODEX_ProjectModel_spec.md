# SPECYFIKACJA `ProjectModel`
## TECH_modul / MSI modul
## Wersja robocza do zatwierdzenia

### Cel dokumentu
Ten dokument opisuje docelowy kontrakt danych dla projektu w aplikacji TECH_modul.
Nie zawiera wdrozenia ani migracji.

### Zakres
Specyfikacja dotyczy obszarow:
- Wycena projektu
- Szybka wycena
- Import 3D
- Uslugi
- Rozkroj / GiB Lab

---

## 1. Rola `ProjectModel`

`ProjectModel` jest wspolnym, wewnetrznym rdzeniem danych projektu.

Ma byc:
- zrodlem prawdy dla aplikacji,
- agregatem laczacym wszystkie obszary projektu,
- warstwa, z ktorej sa budowane widoki, podsumowania i eksporty.

Nie ma zastepowac uzytkownikowi pliku `.project`.

### Zasada uzytkowa
- dla uzytkownika `.project` pozostaje glownym plikiem wymiany i pracy z narzedziami zewnetrznymi,
- dla aplikacji `ProjectModel` jest wewnetrznym zrodlem prawdy.

---

## 2. Zasady projektowe

1. `ProjectModel` ma byc agregatem sekcji, a nie jedna ogromna klasa.
2. Dane maja byc rozdzielone na sekcje funkcjonalne.
3. Kazda sekcja ma miec wlasny kontrakt i byc mozliwa do odczytu osobno.
4. Dane z roznych zrodel maja byc mapowane do wspolnego formatu `quote_lines`.
5. Wycena projektu i Szybka wycena pozostaja biznesowo odrebne, ale korzystaja z tego samego rdzenia danych.
6. Uslugi sa czescia koncowej sumy projektu.
7. Wynik GiB Lab jest czescia projektu, a nie osobnym bytem.

---

## 3. Proponowany kontrakt glowny

```text
ProjectModel
- project_id
- project_name
- project_type
- status
- created_at
- updated_at
- source
- header
- quote_context
- assemblies
- quote_lines
- services
- import_3d
- mapping
- giblab_result
- pricing_snapshot
- audit
```

### Znaczenie pol

- `project_id`
  - wewnetrzny identyfikator projektu.
- `project_name`
  - nazwa widoczna dla uzytkownika.
- `project_type`
  - typ biznesowy projektu, np. komplet, szybka wycena, import 3D.
- `status`
  - stan projektu.
- `created_at`, `updated_at`
  - daty techniczne.
- `source`
  - zrodlo danych, np. UI, `.project`, import, reczna edycja.
- `header`
  - dane naglowkowe i relacyjne.
- `quote_context`
  - aktywny kontekst cenowy.
- `assemblies`
  - komplet / modul / sciana.
- `quote_lines`
  - wspolny format wszystkich pozycji wyceny.
- `services`
  - pozycje uslugowe.
- `import_3d`
  - snapshot danych z `.project`.
- `mapping`
  - mapowanie materialow i elementow z importu.
- `giblab_result`
  - wynik rozkroju i realnego zuzycia.
- `pricing_snapshot`
  - sumy koncowe i skladniki kosztu.
- `audit`
  - metadane pochodzenia i budowy modelu.

---

## 4. Sekcje modelu

### 4.1 `header`

Sekcja naglowkowa projektu.

Minimalne pola:
- `project_name`
- `client_name`
- `order_code`
- `order_name`
- `status`
- `source_kind`
- `source_path`
- `created_at`
- `updated_at`

### 4.2 `quote_context`

Sekcja kontekstu wyceny.

Minimalne pola:
- `mode`
- `pricing_policy`
- `margin_percent`
- `vat_percent`
- `transport_flat`
- `montage_flat`
- `labor_cost`
- `policy_multiplier`

### 4.3 `assemblies`

Sekcja kompletow / modulow / scian.

Kazdy wpis powinien zawierac:
- `assembly_id`
- `name`
- `order_name`
- `client_name`
- `wall_name`
- `dimensions`
- `material_profile`
- `labor_cost`
- `transport_cost`
- `montage_cost`
- `margin_percent`
- `items`

### 4.4 `quote_lines`

Wspolny format wszystkich pozycji wyceny.

Minimalne pola pozycji:
- `line_id`
- `source_kind`
- `source_ref`
- `group`
- `module_name`
- `position_name`
- `qty`
- `unit`
- `length_mm`
- `width_mm`
- `thickness_mm`
- `material_name`
- `edgeband_desc`
- `cost_material`
- `cost_edgeband`
- `cost_labor`
- `cost_extra`
- `line_total`
- `status`
- `accuracy`
- `note`

### 4.5 `services`

Sekcja uslug.

Minimalne pola:
- `service_lines`
- `service_catalog_ref`
- `service_type`
- `price_base`
- `price_transport`
- `price_extra`
- `price_total`
- `price_final`

### 4.6 `import_3d`

Snapshot importu z `.project`.

Minimalne pola:
- `project_path`
- `project_name`
- `project_date`
- `project_version`
- `module_name`
- `module_dimensions`
- `control_rows`
- `summary`
- `import_status`

### 4.7 `mapping`

Mapowanie importu 3D do lokalnej bazy.

Minimalne pola:
- `material_map`
- `edgeband_map`
- `hardware_map`
- `operation_map`
- `mapping_status`
- `last_saved_at`

### 4.8 `giblab_result`

Sekcja wyniku rozkroju.

Minimalne pola:
- `result_path`
- `result_kind`
- `real_sheets_count`
- `real_area_m2`
- `real_edgeband_mb`
- `scrap_m2`
- `leftovers`
- `difference_vs_theory`

### 4.9 `pricing_snapshot`

Koncowe sumy i skladniki wyceny.

Minimalne pola:
- `technical_total`
- `material_value`
- `services_total`
- `extras_total`
- `base_total`
- `sale_total`
- `brutto_total`
- `profit_total`
- `computed_at`

### 4.10 `audit`

Sekcja techniczna do sledzenia zrodla i budowy modelu.

Minimalne pola:
- `built_from`
- `built_at`
- `source_versions`
- `adapter_name`
- `notes`

---

## 5. Zrodla danych

### 5.1 Wycena projektu
Zrodla obecne:
- [src/domain/assembly_models.py](C:/PythonProject/TECH_modul/src/domain/assembly_models.py)
- [src/storage/assembly_store_json.py](C:/PythonProject/TECH_modul/src/storage/assembly_store_json.py)
- [src/storage/order_store_json.py](C:/PythonProject/TECH_modul/src/storage/order_store_json.py)
- [src/storage/quote_pricing_store_json.py](C:/PythonProject/TECH_modul/src/storage/quote_pricing_store_json.py)
- [src/storage/quote_pricing_preset_store_json.py](C:/PythonProject/TECH_modul/src/storage/quote_pricing_preset_store_json.py)
- [src/storage/work_time_store_json.py](C:/PythonProject/TECH_modul/src/storage/work_time_store_json.py)
- [src/storage/worker_store_json.py](C:/PythonProject/TECH_modul/src/storage/worker_store_json.py)
- [src/storage/company_expenses_store_json.py](C:/PythonProject/TECH_modul/src/storage/company_expenses_store_json.py)

### 5.2 Szybka wycena
Zrodla obecne:
- [src/tabs/baza_szybkich_wycen/tab_baza_szybkich_wycen.py](C:/PythonProject/TECH_modul/src/tabs/baza_szybkich_wycen/tab_baza_szybkich_wycen.py)
- `quick_quote_archive.json`
- [src/storage/receptura_store_json.py](C:/PythonProject/TECH_modul/src/storage/receptura_store_json.py)
- [src/services/receptura_bridge_service.py](C:/PythonProject/TECH_modul/src/services/receptura_bridge_service.py)
- [src/storage/quote_pricing_store_json.py](C:/PythonProject/TECH_modul/src/storage/quote_pricing_store_json.py)
- [src/storage/quote_pricing_preset_store_json.py](C:/PythonProject/TECH_modul/src/storage/quote_pricing_preset_store_json.py)

### 5.3 Import 3D
Zrodla obecne:
- [src/tabs/sekcja_do_wyceny/tab_sekcja_do_wyceny.py](C:/PythonProject/TECH_modul/src/tabs/sekcja_do_wyceny/tab_sekcja_do_wyceny.py)
- [src/tabs/wycena/dialog_import_3dc.py](C:/PythonProject/TECH_modul/src/tabs/wycena/dialog_import_3dc.py)
- [src/services/constructor_3dc_quote_import_service.py](C:/PythonProject/TECH_modul/src/services/constructor_3dc_quote_import_service.py)
- [src/services/constructor_3dc_bridge_service.py](C:/PythonProject/TECH_modul/src/services/constructor_3dc_bridge_service.py)
- [src/storage/constructor_3dc_mapping_store_json.py](C:/PythonProject/TECH_modul/src/storage/constructor_3dc_mapping_store_json.py)

### 5.4 Uslugi
Zrodla obecne:
- [src/tabs/uslugi/tab_uslugi.py](C:/PythonProject/TECH_modul/src/tabs/uslugi/tab_uslugi.py)
- [src/storage/service_store_json.py](C:/PythonProject/TECH_modul/src/storage/service_store_json.py)
- [src/domain/service_models.py](C:/PythonProject/TECH_modul/src/domain/service_models.py)

### 5.5 Rozkroj / GiB Lab
Zrodla obecne:
- [src/services/constructor_3dc_bridge_service.py](C:/PythonProject/TECH_modul/src/services/constructor_3dc_bridge_service.py)
- [src/tabs/wycena/dialog_import_3dc.py](C:/PythonProject/TECH_modul/src/tabs/wycena/dialog_import_3dc.py)
- [src/storage/resolved_preview_store_json.py](C:/PythonProject/TECH_modul/src/storage/resolved_preview_store_json.py)

---

## 6. Pierwsze adaptery read-only

Rekomendowana kolejnosc:

1. `QuickQuoteProjectAdapter`
2. `ServiceProjectAdapter`
3. `Import3DProjectAdapter`
4. `PricingContextAdapter`
5. `AssemblyProjectAdapter`
6. `OrderHeaderAdapter`
7. `GibLabResultAdapter`

### Priorytet startowy
Najbezpieczniejszy pierwszy obszar:
- `Szybka wycena`

Powod:
- ma prostszy i bardziej spłaszczony model danych,
- daje szybki test poprawnosci `quote_lines`,
- pozwala sprawdzic `pricing_snapshot` bez wchodzenia od razu w caly komplet.

---

## 7. Plan wdrozenia bez migracji danych

### Etap 1
Zdefiniowac formalny kontrakt `ProjectModel`.

### Etap 2
Dodac adaptery read-only, bez zmian zapisow.

### Etap 3
Zbudowac wewnetrzne snapshoty i porownania wyniku z obecnymi widokami.

### Etap 4
Podpiac `Szybka wycena` jako pierwszy obszar testowy.

### Etap 5
Podpiac `Uslugi` jako osobna sekcje `services` i element `quote_lines`.

### Etap 6
Podpiac `Import 3D` i `mapping`.

### Etap 7
Podpiac `Wycena projektu` jako najtrudniejszy obszar.

### Etap 8
Podpiac `giblab_result`.

### Etap 9
Wprowadzic zapis do nowego modelu dopiero po stabilizacji odczytu.

### Etap 10
Wylaczyc stare sciezki zapisow dopiero po weryfikacji zgodnosci sum i stanów.

---

## 8. Ryzyka

- Rozjazd danych miedzy starymi JSON-ami a nowym modelem.
- Duplikacja semantyki miedzy `OrderDef`, `FurnitureAssemblyDef` i `ServiceOrderDef`.
- Niespojnosc plikow `.project` miedzy wersjami 3DConstructor.
- Zbyt szybkie sciecie starego modelu bez adapterow read-only.
- Pomieszanie biznesowej odrebnosci `Wycena projektu` i `Szybka wycena`.
- Utrata zgodnosci koncowej sumy przez uslugi i korekty po GiB Lab.

---

## 9. Decyzje do zatwierdzenia

1. Czy `ProjectModel` ma byc rdzeniem aplikacji?
2. Czy `.project` zostaje formatem wymiany dla uzytkownika i narzedzi zewnetrznych?
3. Czy JSON-y zostaja przejsciowo jako warstwa trwałosci i fallback?
4. Czy zaczynamy od adapterow read-only?
5. Czy pierwszy obszar testowy to `Szybka wycena`?
6. Czy `quote_lines` staje sie wspólnym formatem pozycji?
7. Czy `Uslugi` i `giblab_result` pozostaja w projekcie jako sekcje?

---

## 10. Zasada koncowa

Najpierw kontrakt, potem adaptery, potem odczyt, dopiero pozniej zapis.
Bez migracji danych na starcie.

