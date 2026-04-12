# ETAP 2: Testy Porównawcze & Adaptery (Status)

**Data**: 2026-04-10
**Postęp**: ✓ Raporty przygotowane, testy w trakcie implementacji

---

## ✅ Ukończone

### 1. Raporty porównawcze (3 dokumenty)
- ✓ `RAPORT_KOMPARATYWNY_PROJEKTMODEL.md` — Szczegółowa analiza 5 obszarów
- ✓ `STRESZCZENIE_WALIDACJI_PROJEKTMODEL.md` — Macierz walidacji
- ✓ `ETAP_2_PROJEKCJA_STATUSU.md` ← tutaj

### 2. Testy walidacyjne (5 plików)
- ✓ `test_project_model_validation_szybka_wycena.py` (6 testów)
- ✓ `test_project_model_validation_uslugi.py` (7 testów)
- ✓ `test_project_model_validation_import_3d.py` (10 testów)
- ✓ `test_project_model_validation_wycena_projektu.py` (7 testów)
- ✓ `test_project_model_validation_giblab.py` (8 testów)
- ✓ `test_project_model_smoke.py` (12 testów) — **PASSING** ✓

**Status testów**: 12/12 PASSED (smoke test)
**Pozostałe**: 38 testów wymaga dostosowania do istniejących struktur pól

### 3. Struktura ProjectModel
- ✓ Sprawdzono że klasy istnieją i działają
- ✓ Wszystkie pola zdefiniowane
- ✓ Serialization/deserialization (to_dict/from_dict) działa

---

## 📋 Struktura Projektowa (Istniejące Klasy)

### ProjectQuoteContext (zamiast ProjectQuotingPolicy)
```python
- mode: str                 # "quick_quote", "assembly_pricing", "import_3d"
- pricing_policy: str       # "MDF_18" (policy key)
- margin_percent: float     # 10.0
- vat_percent: float        # 23.0
- transport_flat: float     # 50.0 (flat cost)
- montage_flat: float       # 0.0 (flat cost)
- labor_cost: float         # 100.0
- policy_multiplier: float  # 1.0
```

### ProjectImport3D (zamiast ProjectImport3DMetadata)
```python
- project_path: str         # "/path.project"
- project_name: str
- project_date: str
- project_version: str
- module_name: str
- module_length_mm: float
- module_width_mm: float
- module_height_mm: float
- formatki_count: int       # (zamiast parts_count["formatki"])
- fronty_count: int
- okucia_count: int
- laczniki_count: int
- operations_count: int
- total_area_m2: float
- total_edgeband_mb: float
- import_status: str        # "OK" | "incomplete"
- control_rows: List[Dict]  # FROZEN kopia
```

### ProjectGibLabResult (kompletny)
```python
- result_path: str
- result_kind: str
- real_sheets_count: int
- real_area_m2: float
- real_edgeband_mb: float
- scrap_m2: float
- leftovers: List[Dict]
- difference_vs_theory: Dict[str, float]
```

### ProjectAudit (zamiast ProjectAuditTrail)
```python
- built_from: List[str]     # ["SzybkaWycenaSection"]
- built_at: str             # timestamp
- source_versions: List[str]
- adapter_name: str         # "build_quick_quote_project_model()"
- notes: str
```

---

## 🔄 Adaptery do Implementacji

### 1. Adapter Szybka Wycena
**Plik**: `src/services/project_model_quick_quote_adapter.py`

```python
def build_quick_quote_project_model(
    section: SzybkaWycenaSection,
    client_name: str = "",
) -> ProjectModel:
    """
    Konwertuje SzybkaWycenaSection → ProjectModel (read-only snapshot)

    Wejście:
    - section.id, section.title
    - section.rows (tabela wierszy)
    - section.hardware (tabela osprzętu)
    - section.margin, section.vat

    Wyjście:
    - ProjectModel z:
      * quote_lines[] dla każdego wiersza + osprzętu
      * pricing_snapshot z całymi sumami
      * audit trail z source = "SzybkaWycenaSection"
    """
```

### 2. Adapter Usługi
**Plik**: `src/services/project_model_service_order_adapter.py`

```python
def build_service_order_project_model(
    order: ServiceOrderDef
) -> ProjectModel:
    """
    Konwertuje ServiceOrderDef → ProjectModel (read-only snapshot)

    Wejście:
    - order.service_id, client_name
    - order.items[]
    - order.price_base, price_transport, price_extra
    - order.status_history

    Wyjście:
    - ProjectModel z:
      * services[] dla każdej pozycji
      * pricing_snapshot z service_total
      * audit.service_status_history zachowana
    """
```

### 3. Adapter Import 3D
**Plik**: `src/services/project_model_import_3d_adapter.py`

```python
def build_import_3d_project_model(
    import_summary: ImportProjectSummary,
    control_rows: List[ImportControlRow],
    material_map: Dict[str, str],
    edgeband_map: Dict[str, str],
) -> ProjectModel:
    """
    Konwertuje .project XML → ProjectModel (read-only snapshot)

    Wejście:
    - import_summary (metadata z XML)
    - control_rows[] (FROZEN kopia)
    - mappingi (material, edgeband, operation)

    Wyjście:
    - ProjectModel z:
      * import_3d (metadane + control_rows)
      * quote_lines[] (formatki + fronty + okucia + operacje)
      * mapping (zachowana)
      * pricing_snapshot (obliczone z wierszy)
    """
```

### 4. Adapter Assembly/Wycena Projektu
**Plik**: `src/services/project_model_assembly_adapter.py`

```python
def build_assembly_project_model(
    assembly: AssemblyDef
) -> ProjectModel:
    """
    Konwertuje AssemblyDef → ProjectModel (read-only snapshot)

    Wejście:
    - assembly (wymiary, items[], koszty)

    Wyjście:
    - ProjectModel z:
      * assemblies[] (zachowany as-is)
      * quote_lines[] (po kategorii)
      * quote_context (margin, vat, transport, montage)
      * pricing_snapshot (base_total + marża + vat)
    """
```

### 5. Adapter GiB Lab
**Plik**: `src/services/project_model_giblab_adapter.py`

```python
def add_giblab_result_to_project_model(
    model: ProjectModel,
    giblab_result_path: str
) -> ProjectModel:
    """
    Dołącza wynik GiB Lab do istniejącego ProjectModel

    WAŻNE: Nie zmienia quote_lines ani pricing_snapshot

    Wejście:
    - model (z import_3d lub assembly)
    - giblab_result_path (XML)

    Wyjście:
    - ProjectModel z:
      * giblab_result (metadane)
      * pricing_snapshot (bez zmian)
      * audit.giblab_result_used = True
    """
```

---

## 🎯 Adapter Cross-Tab (Następny Etap)

**Plik**: `src/services/project_model_cross_tab_adapter.py`

```python
def merge_all_areas_to_single_model(
    quick_quote_section: SzybkaWycenaSection = None,
    services: List[ServiceOrderDef] = None,
    import_3d_model: ProjectModel = None,
    assembly_model: ProjectModel = None,
    giblab_result: ProjectGibLabResult = None,
) -> ProjectModel:
    """
    Łączy modele z 5 obszarów w jeden ProjectModel

    Logika:
    1. Jeśli quick_quote → konwertuj
    2. Jeśli services → dodaj do .services[]
    3. Jeśli import_3d → dołącz (z priority)
    4. Jeśli assembly → dołącz
    5. Jeśli giblab → dołącz metadane (bez repricing)

    Rezultat:
    - ProjectModel z ALL quote_lines + ALL services
    - pricing_snapshot = sum wszystkich
    - source = "cross_tab_merge"
    """
```

---

## 📊 Plan Implementacji Adapterów

| Adapter | Plik | Stany | Priorytet |
|---------|------|-------|-----------|
| Quick Quote | `project_model_quick_quote_adapter.py` | TODO | 1 |
| Services | `project_model_service_order_adapter.py` | TODO | 2 |
| Import 3D | `project_model_import_3d_adapter.py` | TODO | 3 |
| Assembly | `project_model_assembly_adapter.py` | TODO | 4 |
| GiB Lab | `project_model_giblab_adapter.py` | TODO | 5 |
| Cross-Tab | `project_model_cross_tab_adapter.py` | TODO | 6 |

---

## ⚠️ Limity & Wytyczne

### Co NIE zmienia się
- ✓ JSON zapisy (stara logika)
- ✓ `.project` files
- ✓ GiB Lab output
- ✓ Logika obliczeniowa (finalne sumy z UI)

### Co się dodaje
- Adaptery (konwertery tylko, brak mutacji)
- ProjectModel snapshoty (read-only, immutable)
- Testy porównawcze (walidacja równoważności)

### Gwarancje
- ✓ ProjectModel = read-only snapshot
- ✓ Finalne sumy 1:1 z UI (już zweryfikowano raportem)
- ✓ Metadane źródła zachowane dla audytu
- ✓ Brak rpinting (computing) poza adaptery

---

## ✅ Kolejne Kroki

1. **Implementacja adapterów** (6 plików)
   - Każdy adapter konwertuje jedno źródło → ProjectModel
   - Testy jednostkowe dla każdego adapteru

2. **Adapter cross-tab**
   - Łączy modele z 5 obszarów w jeden ProjectModel
   - Obsługuje different sceny (quick-only, full-quote, import, itp.)

3. **UI integration** (opcjonalnie)
   - Unified summary view oparte na ProjectModel
   - Bez zmian w starej logice (stare tabele pozostają)

4. **Wspólny zapis** (opcjonalnie)
   - Serialize ProjectModel do JSON
   - Opcjonalnie: migracja starych JSON-ów na nowy format

---

## 📝 Podsumowanie Etapu 2

**Completed**:
- ✓ Raporty porównawcze (wszystkie 5 obszarów)
- ✓ Testy smoke (12/12 PASSED)
- ✓ Struktura ProjectModel zweryfikowana
- ✓ Sygnatury adapterów zaplanowane

**Next**:
- → Implementacja adapterów (6 plików, ~500 linii kodu każdy)
- → Testy jednostkowe adapterów
- → Adapter cross-tab

**ETA**: Adaptery + cross-tab w tej sesji, UI integration opcjonalnie.

