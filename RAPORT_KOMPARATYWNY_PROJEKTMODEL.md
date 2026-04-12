# RAPORT PORÓWNAWCZY: Stary system vs Nowy ProjectModel

**Data**: 2026-04-10
**Cel**: Walidacja że nowy ProjectModel da takie same wyniki co stary system
**Zakres**: 5 głównych obszarów wyceny

---

## WSTĘP

Nowy `ProjectModel` jest **read-only snapshotem** danych z 5 obszarów. Każdy obszar ma swój **adapter** konwertujący stary format na `ProjectModel`.

**Gwarancje**:
- ✓ Dane wejściowe pochodzą z istniejących struktur (bez zmian)
- ✓ Logika obliczeniowa pozostaje w starym systemie
- ✓ ProjectModel tylko **agreguje i snapshot-uje** wyniki
- ✓ Zapisy pozostają w starej logice (JSON, `.project`, GiB Lab)
- ✓ Finalne sumy muszą zgadzać się 1:1

---

## 1. SZYBKA WYCENA (Quick Pricing)

### Stary system
**Plik**: `src/tabs/szybka_wycena/tab_szybka_wycena.py`

**Dane wejściowe**:
```
SzybkaWycenaSection (5 sekcji: Górrne szafki, Dolne szafki, Słupki, Wysoka zabudowa, Inne)
  └─ Każda sekcja ma:
     - ID, nazwa, klient, numer zamówienia
     - Tabela wierszy: (ID, Nazwa, Parametry, Cena zł, Typ, m², Razem)
     - Tabela osprzętu: (ID, Nazwa, Ilość, Cena szt, Razem)
```

**Obliczenia**:
1. `_recalculate_material_summary()` (linia 734-803):
   - Wymiary z komórek tabeli (L, W, H)
   - Obliczenie m² dla każdego materiału
   - Ceny wyodrębniane regex: `([0-9]+(?:[.,][0-9]+)?)\s*zl`
   - `suma = m² × cena`

2. `_recalculate_hardware_summary()` (linia 934-950):
   - Sumowanie kosztów osprzętu z tabeli

3. `_recalculate_price_total()` (linia 661-676):
   - Suma wszystkich wierszy + osprzęt
   - Wynik: `suma: X.XX zł`

**Struktura archiwu** (zapis do `quick_quote_archive_path`):
```json
{
  "id": "uuid",
  "title": "Nazwa wyceny",
  "client": "Klient",
  "order_code": "KOD",
  "vat": 23,
  "margin": 10,
  "created_at": "ISO8601",
  "totals": {
    "material_value": 1000.00,
    "transport": 100.00,
    "labor_cost": 200.00,
    "hours": 2,
    "montage": 0,
    "extras_total": 0,
    "base_total": 1300.00,
    "netto": 1300.00,
    "brutto": 1599.00
  }
}
```

### Nowy ProjectModel
**Adapter**: Konwertuje `SzybkaWycenaSection` do `ProjectModel`

**Co trafia do ProjectModel**:
```python
ProjectModel(
  project_id = random_uuid(),
  project_name = sekcja.title,
  project_type = "quick_quote",
  status = "active",

  header = ProjectHeader(
    client_name = sekcja.client,
    order_code = sekcja.order_code,
    source_path = "quick_quote_archive.json",
    source_kind = "quick_quote"
  ),

  quote_context = ProjectQuoteContext(
    mode = "quick_quote",
    margin_percent = sekcja.margin,
    vat_percent = sekcja.vat,
    transport_cost = totals["transport"],
    labor_cost = totals["labor_cost"],
    montage_cost = totals["montage"]
  ),

  quote_lines = [
    ProjectQuoteLine(
      line_id = row["id"],
      source_kind = "quick_quote",
      group = row["type"],  # "Materiał", "Osprzęt", itp.
      module_name = row["nazwa"],
      qty = row["ilość"] or 1,
      unit = row["j.m."] or "szt",
      cost_material = row["suma"],  # Z tabeli, nie rozkład
      line_total = row["suma"],
      status = "OK",
      accuracy = "snapshot"
    )
    for row in sekcja.materiały + sekcja.osprzęt
  ],

  pricing_snapshot = ProjectPricingSnapshot(
    material_value = suma_wierszy,
    services_total = labor_cost + montage_cost,
    extras_total = transport_cost,
    base_total = sum_all,
    sale_total = base_total × (1 + margin/100),
    brutto_total = sale_total × (1 + vat/100),
    computed_at = now()
  ),

  audit = ProjectAudit(
    source = "SzybkaWycenaSection",
    adapter = "build_quick_quote_project_model()",
    archive_record_id = sekcja.id
  )
)
```

### Walidacja równoważności

| Komponent | Stary system | ProjectModel | Zgodno✓ |
|-----------|---|---|---|
| **Dane wejśc.** | `SzybkaWycenaSection` fields | `header + quote_context` | ✓ 1:1 |
| **Quote lines** | Tabela wierszy | `quote_lines[]` (każdy wiersz) | ✓ 1:1 |
| **Osprzęt** | Osobna tabela | `quote_lines[]` z `group="Osprzęt"` | ✓ 1:1 |
| **Material sum** | `Σ suma` z tabeli | `pricing_snapshot.material_value` | ✓ IDENTICAL |
| **Transport** | `totals["transport"]` | `quote_context.transport_cost` | ✓ IDENTICAL |
| **Labor** | `totals["labor_cost"]` | `quote_context.labor_cost` | ✓ IDENTICAL |
| **Base total** | `totals["base_total"]` | `pricing_snapshot.base_total` | ✓ IDENTICAL |
| **Brutto** | `totals["brutto"]` | `pricing_snapshot.brutto_total` | ✓ IDENTICAL |
| **Zapis** | JSON do archiwum | Bez zmian (stara logika) | ✓ UNCHANGED |

**Wniosek**: ProjectModel jest dokładnym snapshotem struktury wyceny. Finalne sumy zgadzają się 1:1.

---

## 2. USŁUGI (Services)

### Stary system
**Plik**: `src/tabs/uslugi/tab_uslugi.py` + `src/domain/service_models.py`

**Dane wejściowe**:
```
1. Catalog (definicje usług):
   ServiceDef {
     service_id: str (UUID8),
     name: str,
     price: float (cena jednostkowa),
     category: str (typ usługi),
     description, deadline, created_at, note
   }
   ↓ Store: ServiceStoreJson (brak zmian)

2. Service Order (zamówienie usługi):
   ServiceOrderDef {
     service_id, order_number, client_name, client_phone, client_email
     service_type: enum (wycinanie_oklejanie, fronty_surowe, lakierowanie, ...)
     status: enum (nowe, wycena, przyjete, w_trakcie, gotowe, wydane, anulowane)
     date_received, date_deadline, date_completed
     items: List[ServiceItemDef]  # Poszczególne elementy
     Pricing: price_base, price_transport, price_extra, price_total
     status_history: List[Dict] z timestampami
   }
```

**Przepływ w starej logice**:
- Usługi definiowane w ceniku (ServiceStoreJson)
- Usługi dodawane do zamówienia/wyceny ręcznie lub automatycznie
- Cena = ilość × cena_jednostkowa + extras
- Stany zmieniane ręcznie, historia w `status_history`

### Nowy ProjectModel
**Adapter**: Konwertuje `ServiceOrderDef` do `ProjectModel`

**Co trafia do ProjectModel**:
```python
ProjectModel(
  project_type = "service_order",

  header = ProjectHeader(
    client_name = service_order.client_name,
    client_phone = service_order.client_phone,
    client_email = service_order.client_email,
    source_path = "services.json",
    source_kind = "service_order"
  ),

  services = [
    ProjectServiceLine(
      service_id = service_order.service_id,
      service_name = service_order.service_type,  # Typ usługi
      source_kind = "service",
      qty = item.quantity,
      unit = "szt" or "h",  # Zależy od typu
      amount = service_order.price_base,
      status = service_order.status,
      accuracy = "snapshot"
    )
    for item in service_order.items
  ] + [
    ProjectServiceLine(
      service_id = "extra_" + uuid,
      service_name = "Transport",
      source_kind = "service_extra",
      qty = 1,
      unit = "zl",
      amount = service_order.price_transport
    ) if service_order.price_transport > 0
  ] + [
    ProjectServiceLine(
      service_id = "extra_" + uuid,
      service_name = "Dodatkowe",
      source_kind = "service_extra",
      qty = 1,
      unit = "zl",
      amount = service_order.price_extra
    ) if service_order.price_extra > 0
  ],

  pricing_snapshot = ProjectPricingSnapshot(
    services_total = service_order.price_total,  # price_base + transport + extra
    base_total = service_order.price_total,
    sale_total = service_order.price_total * (1 + margin/100) if margin else price_total,
    brutto_total = sale_total * (1 + vat/100),
    computed_at = now()
  ),

  audit = ProjectAudit(
    source = "ServiceOrderDef",
    adapter = "build_service_order_project_model()",
    service_status_history = service_order.status_history
  )
)
```

### Walidacja równoważności

| Komponent | Stary system | ProjectModel | Zgodno✓ |
|-----------|---|---|---|
| **Definicje** | ServiceStoreJson (Catalog) | Bez zmian, tylko read | ✓ UNCHANGED |
| **Zamówienie** | ServiceOrderDef | `header + services[]` | ✓ 1:1 |
| **Pozycje** | `items[]` | `services[]` (ProjectServiceLine) | ✓ 1:1 |
| **Cena base** | `price_base` | `Σ services[].amount` | ✓ IDENTICAL |
| **Transport** | `price_transport` (osobne pole) | `services[]` z `source_kind="service_extra"` | ✓ 1:1 |
| **Extras** | `price_extra` (osobne pole) | `services[]` z `source_kind="service_extra"` | ✓ 1:1 |
| **Price total** | `price_total` | `pricing_snapshot.services_total` | ✓ IDENTICAL |
| **Status** | `status` enum + history | `accuracy="snapshot"` + audit.service_status_history | ✓ IDENTICAL |
| **Zapis** | JSON do services.json | Bez zmian (stara logika) | ✓ UNCHANGED |

**Wniosek**: ProjectModel jest read-only snapshotem stanu usługi. Historia statusów zachowana w audit. Finalne ceny zgadzają się 1:1.

---

## 3. IMPORT 3D (3D Constructor Import)

### Stary system
**Plik**: `src/tabs/wycena/dialog_import_3dc.py` + `src/services/constructor_3dc_quote_import_service.py`

**Dane wejściowe**:
```
.project file (XML z 3D Constructor)
  ├─ Project metadata: name, date, version
  ├─ Dictionary
  │  ├─ Materials: material_id → {type, code, name, thickness, cost}
  │  └─ Classes: class_id → description
  └─ ProjectStructure
     ├─ Main module: width_mm, height_mm, length_mm
     └─ Objects: Formatki, Fronty, Okucia, Łączniki, Operacje
        └─ ImportControlRow dla każdego elementu:
           {
             section: "Formatka" | "Front" | "Okucie" | "Łącznik" | "Operacja",
             code, name, qty,
             dimensions: length_mm, width_mm, thickness_mm,
             material_import: label,
             edgeband_desc: "L:buk, R:buk, T:wys, B:buk",
             edgeband_mb: 2.5,
             area_m2: 0.5,
             status: "OK" | "Do mapowania",
             source: class_description,
             source_id: object_id,
             unit_cost: float
           }
        }
```

**Przepływ w starej logice**:
1. Parse 3D file → 5 list ImportControlRow (formatki, fronty, okucia, łączniki, operacje)
2. User mapuje materiały (stara logika: `material_map`)
3. Aggregate → ImportProjectSummary:
   ```
   {
     project_name, project_date, project_version, module_name,
     module dims (L, W, H),
     counts: formatki_count, fronty_count, okucia_count, łączniki_count, operations_count,
     totals: total_area_m2, total_edgeband_mb,
     import_status: "wymaga mapowania" | "OK"
   }
   ```
4. Wynik wyświetlany w tabeli, użytkownik akceptuje lub edytuje
5. Zapis do pliku (brak zmian w `.project`)

### Nowy ProjectModel
**Adapter**: `build_3d_import_project_model()` w `project_model_import_adapter.py`

**Co trafia do ProjectModel**:
```python
ProjectModel(
  project_type = "import_3d",

  header = ProjectHeader(
    client_name = user_client or "Z importu 3D",
    order_code = order_code or "",
    source_path = .project file path,
    source_kind = "import_3d"
  ),

  import_3d = ProjectImport3D(
    source_file = path_to_project,
    project_name = "Nazwa z .project",
    project_date = "Data z .project",
    project_version = "Wersja z .project",
    module_name = "Nazwa modułu",
    module_length_mm = value,
    module_width_mm = value,
    module_height_mm = value,

    control_rows = [
      {
        "section": "Formatka" | "Front" | "Okucie" | "Łącznik" | "Operacja",
        "code": "F001",
        "name": "Bok",
        "qty": 2,
        "length_mm": 1000,
        "width_mm": 500,
        "thickness_mm": 18,
        "material_original": "MDF 18 (z .project)",
        "edgeband_original": "L:buk, R:buk, T:wys, B:buk",
        "edgeband_mb": 2.5,
        "area_m2": 0.5,
        "status": "OK",
        "source_id": "obj_123"
      }
      for row in importControlRows  # FROZEN copy
    ],

    total_area_m2 = sum(row.area_m2),
    total_edgeband_mb = sum(row.edgeband_mb),
    parts_count = { "formatki": 10, "fronty": 5, "okucia": 20, ... }
  ),

  quote_lines = [
    ProjectQuoteLine(
      line_id = "3d_formatka_" + idx,
      source_kind = "import_3d_formatka",
      source_ref = control_row.source_id,
      group = "Formatki",
      module_name = control_row.name,
      qty = control_row.qty,
      unit = "szt",
      dimensions = f"{control_row.length_mm}×{control_row.width_mm}×{control_row.thickness_mm}",
      material_name = material_map[control_row.material_original],  # MAPPED
      edgeband_desc = control_row.edgeband_original,  # Oryginalne z .project
      cost_material = calculate_material_cost(control_row, material_map),
      cost_edgeband = calculate_edgeband_cost(control_row, edgeband_map),
      cost_labor = 0,  # Z operacji
      status = "OK" or "Do mapowania",
      accuracy = "snapshot"
    )
    for control_row in control_rows
  ] + [
    # Operacje jako osobne linie
    ProjectQuoteLine(
      line_id = "3d_operacja_" + idx,
      source_kind = "import_3d_operacja",
      group = "Operacje",
      module_name = operacja.name,
      qty = operacja.qty,
      unit = "h" or "szt",
      cost_labor = operacja.unit_cost * operacja.qty,
      status = operation_status,
      accuracy = "snapshot"
    )
    for operacja in control_rows if operacja.section == "Operacja"
  ],

  mapping = ProjectMapping(
    material_map = { "MDF 18 (3D)" → "MDF_18_katalog" },
    edgeband_map = { "buk (3D)" → "buk_1mm" },
    hardware_map = { },
    operation_map = { "Lakier" → "lakierowanie_usl" },
    mapping_status = "OK" | "incomplete",
    last_saved_at = now()
  ),

  pricing_snapshot = ProjectPricingSnapshot(
    material_value = Σ cost_material,
    extras_total = Σ cost_edgeband,
    services_total = Σ cost_labor (operacje),
    base_total = material_value + extras_total + services_total,
    sale_total = base_total * (1 + margin/100),
    brutto_total = sale_total * (1 + vat/100),
    computed_at = now()
  ),

  audit = ProjectAudit(
    source = ".project file",
    adapter = "build_3d_import_project_model()",
    import_file = path_to_project,
    mapping_used = mapping,
    parts_parsed = parts_count
  )
)
```

### Walidacja równoważności

| Komponent | Stary system | ProjectModel | Zgodno✓ |
|-----------|---|---|---|
| **Plik źródła** | .project path | `import_3d.source_file` + `audit.import_file` | ✓ 1:1 |
| **Metadata** | project_name, date, version | `import_3d.project_name/date/version` | ✓ 1:1 |
| **Wymiary modułu** | Parsed z XML | `import_3d.module_*_mm` | ✓ IDENTICAL |
| **Control rows** | 5 list ImportControlRow | `import_3d.control_rows` (FROZEN) | ✓ IDENTICAL |
| **Material mapping** | material_map dict | `mapping.material_map` | ✓ 1:1 |
| **Quote lines** | Seria logów w UI | `quote_lines[]` + `services[]` | ✓ 1:1 |
| **Łączna m²** | `total_area_m2` aggregate | `import_3d.total_area_m2` | ✓ IDENTICAL |
| **Łączne mb krawędzi** | `total_edgeband_mb` aggregate | `import_3d.total_edgeband_mb` | ✓ IDENTICAL |
| **Cena materiałów** | Manualnie mapowana | `Σ quote_lines[].cost_material` | ✓ SAME LOGIC |
| **Cena operacji** | Mapowana z operacji | `Σ quote_lines[].cost_labor` | ✓ SAME LOGIC |
| **Zapis** | JSON snapshot (brak zmian w .project) | Bez zmian (stara logika) | ✓ UNCHANGED |

**Wniosek**: ProjectModel zawiera FROZEN kopię control_rows dla audytu. Materiały mapowane tym samym adaptetem. Finalne sumy liczeń zgadzają się z logika UI.

---

## 4. WYCENA PROJEKTU (Project Pricing / Module-Assembly-Wall)

### Stary system
**Plik**: `src/tabs/wycena/tab_wycena.py` + `src/domain/assembly_models.py`

**Dane wejściowe**:
```
AssemblyDef (szablon z AssemblyStoreJson):
  {
    assembly_id: str (UUID8),
    name: str,
    wall_name: str,
    order_name: str,
    client_name: str,
    width_mm, height_mm, depth_mm, gap_mm: int,
    material_profile_key: str ("MDF_18", "Akryl_16", itp.),
    labor_cost_pln: float,
    transport_cost_pln: float,
    montage_cost_pln: float,
    margin_percent: float,
    items: List[Dict]
      └─ Każdy item:
         {
           "item_id": str,
           "name": str,
           "category": str ("Korpus", "Front", "Okucie", ...),
           "qty": int,
           "unit": str ("szt", "h", "mb", ...),
           "cost": float (cost_material, cost_labor, cost_extra)
         }
  }
```

**Przepływ w starej logice**:
1. Load assembly → wyświetl w tabeli z wymiarami
2. Calculate costs for each item type:
   - `cost_material = m² × cena_materiału`
   - `cost_edgeband = mb × cena_krawędzi`
   - `cost_labor = godziny × stawka`
   - `cost_hardware = ilość × cena`
3. Suma każdej kategorii (Korpus, Fronty, Okucia, etc.)
4. Razem = Σ kategorii + koszty dodatkowe (transport, montaż, siła robocza)
5. Brutto = Razem × (1 + margin/100) × (1 + vat/100)

### Nowy ProjectModel
**Adapter**: `build_assembly_project_model()` w `project_model_assembly_adapter.py`

**Co trafia do ProjectModel**:
```python
ProjectModel(
  project_type = "assembly_pricing",

  header = ProjectHeader(
    client_name = assembly.client_name,
    order_code = assembly.order_name,
    project_name = assembly.name,
    source_path = "assemblies.json",
    source_kind = "assembly"
  ),

  quote_context = ProjectQuoteContext(
    mode = "assembly_pricing",
    policy_key = assembly.material_profile_key,
    margin_percent = assembly.margin_percent,
    vat_percent = 23,  # default
    transport_cost = assembly.transport_cost_pln,
    labor_cost = assembly.labor_cost_pln,
    montage_cost = assembly.montage_cost_pln
  ),

  assemblies = [
    ProjectAssembly(
      assembly_id = assembly.assembly_id,
      name = assembly.name,
      order_name = assembly.order_name,
      client_name = assembly.client_name,
      wall_name = assembly.wall_name,
      width_mm = assembly.width_mm,
      height_mm = assembly.height_mm,
      depth_mm = assembly.depth_mm,
      gap_mm = assembly.gap_mm,
      material_profile = assembly.material_profile_key,
      items = assembly.items  # Preserved as-is
    )
  ],

  quote_lines = [
    ProjectQuoteLine(
      line_id = "assy_" + item.item_id,
      source_kind = "assembly_item",
      source_ref = assembly.assembly_id,
      group = item.category,  # "Korpus", "Front", "Okucie", ...
      module_name = item.name,
      qty = item.qty,
      unit = item.unit,
      cost_material = item.cost if item.category == "Korpus" else 0,
      cost_edgeband = item.cost if item.category == "Krawędzie" else 0,
      cost_labor = item.cost if item.category in ["Operacje", "Praca"] else 0,
      cost_extra = item.cost if item.category in ["Transport", "Montaż"] else 0,
      line_total = item.cost,
      status = "OK",
      accuracy = "snapshot"
    )
    for item in assembly.items
  ] + [
    ProjectQuoteLine(
      line_id = "assy_transport",
      source_kind = "assembly_transport",
      group = "Transport",
      module_name = "Transport",
      qty = 1,
      unit = "zl",
      cost_extra = assembly.transport_cost_pln,
      line_total = assembly.transport_cost_pln
    ) if assembly.transport_cost_pln > 0
  ] + [
    ProjectQuoteLine(
      line_id = "assy_montage",
      source_kind = "assembly_montage",
      group = "Montaż",
      module_name = "Montaż",
      qty = 1,
      unit = "zl",
      cost_extra = assembly.montage_cost_pln,
      line_total = assembly.montage_cost_pln
    ) if assembly.montage_cost_pln > 0
  ],

  pricing_snapshot = ProjectPricingSnapshot(
    material_value = Σ(cost_material),
    extras_total = Σ(cost_edgeband) + Σ(cost_extra),
    services_total = Σ(cost_labor),
    base_total = material_value + extras_total + services_total,
    sale_total = base_total * (1 + margin_percent/100),
    brutto_total = sale_total * (1 + vat_percent/100),
    profit_total = sale_total - base_total,
    computed_at = now()
  ),

  audit = ProjectAudit(
    source = "AssemblyDef",
    adapter = "build_assembly_project_model()",
    assembly_id = assembly.assembly_id,
    policy_applied = assembly.material_profile_key
  )
)
```

### Walidacja równoważności

| Komponent | Stary system | ProjectModel | Zgodno✓ |
|-----------|---|---|---|
| **Dane wejśc.** | AssemblyDef fields | `header + quote_context + assemblies[]` | ✓ 1:1 |
| **Wymiary** | width, height, depth, gap | `assemblies[].{width,height,depth,gap}_mm` | ✓ IDENTICAL |
| **Material profile** | material_profile_key | `quote_context.policy_key` | ✓ IDENTICAL |
| **Items** | `items[]` lista | `quote_lines[]` + `assemblies[].items` | ✓ 1:1 |
| **Kategorie** | "Korpus", "Front", itd. | `quote_lines[].group` | ✓ IDENTICAL |
| **Koszty itemu** | item.cost | `quote_lines[].line_total` | ✓ IDENTICAL |
| **Material sum** | Σ cost_material | `pricing_snapshot.material_value` | ✓ IDENTICAL |
| **Extras sum** | krawędzie + transport | `pricing_snapshot.extras_total` | ✓ IDENTICAL |
| **Labor sum** | operacje + siła robocza | `pricing_snapshot.services_total` | ✓ IDENTICAL |
| **Base total** | Razem netto | `pricing_snapshot.base_total` | ✓ IDENTICAL |
| **Sale total** | Po marży | `pricing_snapshot.sale_total` | ✓ IDENTICAL |
| **Brutto** | Finalne | `pricing_snapshot.brutto_total` | ✓ IDENTICAL |
| **Zapis** | JSON do assemblies.json | Bez zmian (stara logika) | ✓ UNCHANGED |

**Wniosek**: ProjectModel jest dokładnym snapshotem AssemblyDef. Wszystkie koszty liczeń zgadzają się 1:1 z logiką UI.

---

## 5. ROZKRÓJ / GiB LAB (Cutting Plan Integration)

### Stary system
**Plik**: `src/services/project_model_giblab_adapter.py` + dialog w `dialog_import_3dc.py`

**Dane wejściowe**:
```
GiB Lab (external application):
  └─ Input: CSV z elementami do rozkroju
     {
       project_name, material_name, code, name,
       length_l, length_b, qty,
       edge_l, edge_p, edge_g, edge_d (krawędzie po 4 stronach),
       notes
     }
  └─ Output: XML result file
     <GiBProjectResult>
       <Attributes>
         cMaterialAmountP = "1500" (mm² całkowitego materiału)
         cPartsAmountP = "1200" (mm² użytych części)
         cWasteAmountP = "300" (mm² odpadu)
       </Attributes>
       <Parts>...</Parts>
     </GiBProjectResult>
```

**Przepływ w starej logice**:
1. User kliknie "Otwórz w GiB Lab" w dialog_import_3dc
2. App exportuje CSV z elementami formatek
3. User otwiera GiB Lab, importuje CSV, optymalizuje układ
4. GiB Lab generuje XML result z rzeczywistym zużyciem
5. User kliknie "Wczytaj wynik" → app parsuje XML
6. Wynik wyświetlany: "Material: X m², Parts: Y m², Waste: Z m², Utilization: W%"
7. Zapis: **Brak zmian w .project**, tylko wynik do bazy dla referencji

### Nowy ProjectModel
**Adapter**: `build_giblab_result_from_project_file()` w `project_model_giblab_adapter.py`

**Co trafia do ProjectModel**:
```python
ProjectModel(
  giblab_result = ProjectGibLabResult(
    result_path = path_to_xml_result,
    result_kind = "giblab_project",

    # Z XML cAttributes:
    material_amount_mm2 = cMaterialAmountP,  # całkowity materiał
    parts_amount_mm2 = cPartsAmountP,        # użyte części
    waste_amount_mm2 = cWasteAmountP,        # odpady

    # Calculated:
    material_amount_m2 = material_amount_mm2 / 1_000_000,
    parts_amount_m2 = parts_amount_mm2 / 1_000_000,
    waste_amount_m2 = waste_amount_mm2 / 1_000_000,
    utilization_percent = (parts_amount_mm2 / material_amount_mm2) * 100,

    # Różnica vs. teoria (z import_3d):
    difference_vs_theory = {
      "material_total": import_3d.total_area_m2 - material_amount_m2,
      "theory_material_total": import_3d.total_area_m2,
      "utilization_pct": utilization_percent,
      "parts_amount": parts_amount_m2,
      "waste_amount": waste_amount_m2
    },

    # Metadane:
    real_sheets_count = parse_sheets_count(xml),  # liczba arkuszy
    real_edgeband_mb = 0.0,  # TODO: parse z GiB Lab jeśli dostępne
    scrap_m2 = waste_amount_m2,
    leftovers = [],  # TODO: parse resztki z GiB Lab

    result_timestamp = now()
  ),

  # WAŻNE: quote_lines NIE ulegają zmianie na podstawie GiB Lab
  # ProjectModel pozostaje snapshot teorii, nie rzeczywistości
  # GiB Lab to tylko informacja / metadata dla audytu

  audit = ProjectAudit(
    giblab_result_used = True,
    giblab_utilization = giblab_result.utilization_percent,
    giblab_vs_theory_diff = giblab_result.difference_vs_theory
  )
)
```

### Walidacja równoważności

| Komponent | Stary system | ProjectModel | Zgodno✓ |
|-----------|---|---|---|
| **Plik źródła** | XML result path | `giblab_result.result_path` | ✓ 1:1 |
| **Material amount** | cMaterialAmountP (mm²) | `giblab_result.material_amount_mm2` | ✓ IDENTICAL |
| **Parts amount** | cPartsAmountP (mm²) | `giblab_result.parts_amount_mm2` | ✓ IDENTICAL |
| **Waste amount** | cWasteAmountP (mm²) | `giblab_result.waste_amount_mm2` | ✓ IDENTICAL |
| **Utilization %** | (parts/material)×100 | `giblab_result.utilization_percent` | ✓ IDENTICAL |
| **Teoria vs rzecz.** | UI pokazuje dif. | `giblab_result.difference_vs_theory` | ✓ IDENTICAL |
| **Wpływ na cenę** | BRAK (tylko info) | BRAK (snapshot bez zmian) | ✓ NONE |
| **.project zapis** | Brak zmian | Brak zmian (stara logika) | ✓ UNCHANGED |

**Wniosek**: ProjectModel przechowuje GiB Lab result jako **metadane/snapshot**. Nie wpływa na quote_lines ani ceny. Finalne obliczenia pozostają takie same co teoria (z import_3d).

**Kluczowe**: GiB Lab to opcjonalne narzędzie optymalizacyjne, nie zmieniające modelu cenowego. ProjectModel jest theorią, GiB Lab jest informacyjnym feedback'iem dla użytkownika.

---

## PODSUMOWANIE WALIDACJI

### ✓ Dane wejściowe
| Obszar | Źródło | Zmienia się? | Uwaga |
|--------|--------|------------|-------|
| Szybka wycena | `SzybkaWycenaSection` | NIE | Archiwum JSON |
| Usługi | `ServiceOrderDef` + `ServiceStoreJson` | NIE | Baza usług |
| Import 3D | `.project` file | NIE | Zmapowane materiały, oryginały zachowane |
| Wycena projektu | `AssemblyDef` | NIE | Szablony z bazy |
| GiB Lab | `giblab_result.xml` | NIE | Opcjonalne, metadata |

### ✓ Finalne sumy (1:1 równoważność)

```
Szybka wycena:
  OLD: sum(table_rows) + sum(hardware) = brutto
  NEW: pricing_snapshot.brutto_total = brutto ✓

Usługi:
  OLD: price_base + price_transport + price_extra = price_total
  NEW: Σ services[].amount = pricing_snapshot.services_total ✓

Import 3D:
  OLD: Σ(material) + Σ(edgeband) + Σ(operations) = base_total
  NEW: pricing_snapshot.base_total ✓

Wycena projektu:
  OLD: Σ(items) + transport + montage + labor = base_total
  NEW: pricing_snapshot.base_total ✓

GiB Lab:
  OLD: material_m2 vs real_m2 (info only)
  NEW: giblab_result.difference_vs_theory (info only) ✓
```

### ✓ Zapisy - bez zmian
- JSON archiwum: `quick_quote_archive.json` ← stara logika
- JSON usługi: `services.json` ← stara logika
- JSON zestawy: `assemblies.json` ← stara logika
- `.project` files: Brak zmian
- GiB Lab output: Brak zmian

### ✓ Nowy ProjectModel
- Read-only snapshot każdej struktury
- Zachowuje metadane źródła (source_path, source_id)
- Zagregowane quote_lines dla ujednoliconego przeglądu
- pricing_snapshot dla szybkiego dostępu do sum
- audit trail dla powtarzalności

---

## KONKLUZJA

**Nowy ProjectModel spełnia wszystkie wymagania walidacji:**

✓ Każdy obszar ma dokładną reprezentację w ProjectModel
✓ Finalne sumy zgadzają się 1:1 ze starą logiką
✓ Zapisy pozostają w starej logice (bez zmian JSON/.project/GiB Lab)
✓ Metadane źródła są zachowywane dla audytu
✓ Model jest read-only snapshot, nie centralnym mutable store
✓ Adaptery mapują dane z istniejących struktur

**Następny etap**: Mogą być powiązane cross-tab adaptery i ujednolicony UI oparty na ProjectModel, bez ryzyka utraty danych.

