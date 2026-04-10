# Reguły Łączenia Źródeł w ProjectModel / Unified Summary

**Data**: 2026-04-10
**Status**: DRAFT — wymaga zatwierdzenia
**Cel**: Zdefiniować biznesowe warunki, kiedy i jak łączyć dane z różnych źródeł wyceny

---

## 1. ŹRÓDŁA BAZOWE (Base Pricing Source)

### Definicja
Jeden i tylko jeden **aktywny** system wyceny jest w danym momencie podstawą:

| Źródło | ID | Opis | Kontekst |
|--------|----|----|---------|
| **Wycena projektu** | `assembly` | Pełna wycena na bazie struktury modułów/kompletów/ścian | Długo- i średnioterminowe projekty |
| **Szybka wycena** | `quick_quote` | Uproszczona wycena bez pełnej struktury projektu | Oferty ad-hoc, przedwstępne kalkulacje |
| **Import 3D** | `import_3d` | Wycena wyekstrahowana z pliku .project (3D Constructor / CAD) | Projekty z zewnętrznych systemów |

### Reguła #1: Jeden aktywny źródło bazowe
```
W każdym momencie dla danego kontekstu (order_code, client_name):
- TYLKO JEDNO z trzech powyższych jest bazą do wyceny
- Inne są ignorowane w merge'u
- Przełączenie między nimi anuluje poprzedni kontekst
```

### Reguła #2: Priorytet źródeł
Jeśli użytkownik jest w danym momencie w konkretnej zakładce:
```
Zakładka aktywna (tab_wycena_hub) → określa które źródło jest bazowe:

[Wycena projektu] ← aktywna → źródło bazowe = assembly
[Szybka wycena] ← aktywna → źródło bazowe = quick_quote
[Import 3D] ← aktywna → źródło bazowe = import_3d
[Rozkrój] → nie określa źródła (pasywny)
[Podsumowanie] → pokazuje aktualnie bazowe + dołączane
```

---

## 2. ŹRÓDŁA DOŁĄCZANE (Supplementary Sources)

### Definicja
Źródła, które **mogą być** doliczane do bazowego (ale nie muszą):

| Źródło | ID | Opis | Warunki dołączenia |
|--------|----|----|---------|
| **Usługi** | `service` | Pozycje dodatkowe (lakierowanie, transport, montaż, serwis) | Zawsze dostępne; doliczane jeśli dodane |
| **GiB Lab** | `giblab` | Wynik rozkroju — metadane, nie wycena | NIGDY nie sumować; tylko info/feedback |

### Reguła #3: Usługi są zawsze opcjonalne
```
if (usługi są w bazie i użytkownik je wybrał):
    base_total += sum(services[].amount)
else:
    # nie doliczaj
    pass
```

### Reguła #4: GiB Lab NIGDY nie jest wycenią
```
giblab_result ≠ pricing_snapshot

GiB Lab to TYLKO:
- Informacja o rzeczywistym rozkroju (real_sheets_count, real_area_m2, scrap_m2)
- Porównanie do teorii (difference_vs_theory.utilization_pct)
- Feedback / audyt dla wybranego źródła bazowego

GiB Lab NIE SUMUJE się z base_total!!!
```

---

## 3. METADANE I FEEDBACK (Metadata / Audit)

### GiB Lab — Wynik, nie Wycena
```python
# Przykład: wycena projektu = 5000 zl (base_total)
# Import z 3D Constructor i GiB Lab

merged_model = {
    "source_base": "import_3d",
    "pricing_snapshot": {
        "base_total": 5000.00,  # ← z import_3d
        "brutto_total": 6150.00,  # 5000 * 1.23 VAT
    },
    "giblab_result": {
        "result_path": "/gib/lab/output/rozkroj_001.txt",
        "real_area_m2": 12.5,        # ← Real result
        "real_sheets_count": 4,      # ← Real result
        "scrap_m2": 0.75,            # ← Real result
        "difference_vs_theory": {
            "utilization_pct": 94.2,
            "loss_vs_theory_pct": -2.1  # ← Negative = lepiej niż się spodziewaliśmy
        }
    },
    "audit": {
        "notes": "Based on import_3d; GiB Lab provides feedback, not pricing"
    }
}

# GiB Lab result jest DODATKIEM do informacji, nie zmienia base_total
```

### Reguła #5: GiB Lab jest tylko feedback'iem
```
giblab_metrics ≠ cost to add
giblab_metrics = quality info / audyt

Jeśli użytkownik chce zmienić cenę na bazie GiB Lab (np. dodać surcharge za straty):
→ To musi być RĘCZNE dodanie serwisu/dodatkowego kosztu
→ NIE AUTOMATYCZNE z GiB Lab

# Zły przykład:
merged.pricing_snapshot.base_total += giblab_result.scrap_m2 * price_per_m2  # ❌ WRONG

# Dobry przykład:
if user_wants_scrap_surcharge:
    new_service = {
        "service_name": "Surcharge za opady (GiB Lab audit)",
        "amount": giblab_result.scrap_m2 * price_per_m2
    }
    services.append(new_service)  # ✓ User controls it
```

---

## 4. WARUNKI MERGE (Merge Conditions)

### Reguła #6: Merge jest dozwolony tylko jeśli:

```python
def is_merge_allowed(models: list[ProjectModel], merge_reason: str) -> bool:
    """
    Warunki konieczne do merge:
    """

    # Warunek 1: Jeden i tylko jeden model z group [assembly, quick_quote, import_3d]
    base_models = [m for m in models
                   if m.project_type in ['assembly', 'quick_quote', 'import_3d']]
    if len(base_models) != 1:
        return False  # ❌ Albo 0 albo 2+ modele bazowe = BŁĄD

    # Warunek 2: Jeśli więcej niż jedno źródło bazowe wybrane
    if merge_reason == "user_explicit_multi_source":
        # ✓ Dozwolone TYLKO jeśli użytkownik wyraźnie powiedział "połącz to"
        # Wymaga potwierdzenia w UI
        return True

    # Warunek 3: Usługi mogą być dodane do bazowego źródła
    service_models = [m for m in models if m.project_type == 'service_order']
    if len(service_models) > 1:
        return False  # ❌ Maksymalnie jedna usługi order

    # Warunek 4: GiB Lab nigdy nie zmienia ceny
    giblab_models = [m for m in models if m.project_type == 'giblab']
    if len(giblab_models) > 0:
        # ✓ Dozwolone, ale GiB Lab będzie TYLKO metadane
        # Nie zmienia pricing_snapshot
        return True

    return True
```

### Scenariusze Merge — Dozwolone

#### Scenariusz A: Samo źródło bazowe
```
User w [Wycena projektu], brak usług, brak GiB Lab
→ merge_project_models([assembly_model])
→ Unified Summary pokazuje samą wycenę projektu
✓ DOZWOLONE
```

#### Scenariusz B: Źródło bazowe + Usługi
```
User w [Wycena projektu]
User dodał 2 pozycje usług (lakier + transport)

→ merge_project_models([assembly_model, service_order_model])
→ base_total = assembly.base + sum(services)
→ Unified Summary: assembly + usługi
✓ DOZWOLONE
```

#### Scenariusz C: Źródło bazowe + GiB Lab
```
User w [Import 3D]
Import 3D model wygenerowany z .project
GiB Lab wynik dostępny

→ merge_project_models([import_3d_model])
→ giblab_result attached as metadata
→ pricing_snapshot = TYLKO z import_3d
→ Unified Summary: pricing z import_3d + GiB Lab feedback
✓ DOZWOLONE
```

#### Scenariusz D: Źródło bazowe + Usługi + GiB Lab
```
User w [Import 3D]
Import 3D model + 1 usługa dodana + GiB Lab dostępny

→ merge_project_models([import_3d_model, service_order_model])
→ base_total = import_3d.base + sum(services)
→ giblab_result attached
→ Unified Summary: all three
✓ DOZWOLONE
```

### Scenariusze Merge — ZAKAZANE

#### ❌ Scenariusz 1: Dwa źródła bazowe naraz bez zgody
```
User przełączył z [Wycena projektu] na [Szybka wycena]
Ale obie mają już wygenerowane modele

→ merge_project_models([assembly_model, quick_quote_model])
→ base_total = assembly.base + quick_quote.base
❌ ZAKAZANE — podwójne liczenie!
```

#### ❌ Scenariusz 2: 2+ usługi orders
```
→ merge_project_models([assembly_model, service_order_1, service_order_2])
❌ ZAKAZANE — 2 źródła usług = niejedoznaczne
```

#### ❌ Scenariusz 3: GiB Lab zmienia ceny
```
if merge_reason == "auto_apply_giblab_cost_correction":
    # ❌ ZAKAZANE — nigdy nie zmieniaj base_total na bazie GiB Lab
    merged.pricing_snapshot.base_total += giblab_correction
    # To byłoby BŁĘDEM biznesowym!
```

---

## 5. BLOKOWANIE NIEBEZPIECZNYCH MERGE'ÓW (Safety Guards)

### Reguła #7: Detektuj i blokuj niebezpieczne scenariusze

```python
def validate_merge(models: list[ProjectModel]) -> tuple[bool, str]:
    """
    Zwraca: (is_valid, error_message)
    """

    # Guard 1: Ile źródeł bazowych?
    base_types = {'assembly', 'quick_quote', 'import_3d'}
    base_models = [m for m in models if m.project_type in base_types]

    if len(base_models) == 0:
        return False, "Brak źródła bazowego wyceny"

    if len(base_models) > 1:
        return False, f"Błąd: {len(base_models)} źródła bazowe. " \
                      "Może być tylko jedno. " \
                      "Jeśli chcesz połączyć wyceny, " \
                      "użyj 'Porównanie wycen' (Etap future)"

    # Guard 2: Ile usług?
    service_models = [m for m in models if m.project_type == 'service_order']
    if len(service_models) > 1:
        return False, "Błąd: 2+ source usług. " \
                      "Może być maksymalnie 1."

    # Guard 3: GiB Lab nie zmienia pricing
    giblab_models = [m for m in models if m.project_type == 'giblab']
    if giblab_models:
        # ✓ Info, że GiB Lab będzie tylko feedbackiem
        pass

    return True, ""
```

### Implementacja w merge_project_models()

```python
def merge_project_models(models, ...) -> ProjectModel:
    is_valid, error = validate_merge(models)
    if not is_valid:
        raise ValueError(f"Merge safety check failed: {error}")

    # ... reszta merge logic
```

---

## 6. PREZENTACJA W UI — BRAK PODWÓJNEGO LICZENIA

### Reguła #8: Unified Summary musi jasno pokazać źródło każdej sumy

```
┌─────────────────────────────────────────────┐
│ Ujednolicone Podsumowanie Wyceny            │
├─────────────────────────────────────────────┤
│                                             │
│ Źródło bazowe: Wycena projektu (assembly)  │ ← Jasne!
│ Inne źródła: Usługi (1 pozycja)             │
│                                             │
├─────────────────────────────────────────────┤
│ PRICING BREAKDOWN                           │
├─────────────────────────────────────────────┤
│ Materiały       2500.00 zl  [assembly]      │ ← Źródło!
│ Transport        100.00 zl  [assembly]      │
│ Robocizna        300.00 zl  [assembly]      │
│ ────────────────────────────────────────────│
│ Razem netto     2900.00 zl  [aggregate]     │
│                                             │
│ Usługi dodatkowe 500.00 zl  [services]      │ ← Inne źródło!
│ ────────────────────────────────────────────│
│ RAZEM bazowe    3400.00 zl                  │
│ Marża 10%        340.00 zl                  │
│ Brutto (VAT)    4182.00 zl                  │
│                                             │
├─────────────────────────────────────────────┤
│ ŹRÓDŁA DANYCH                               │
├─────────────────────────────────────────────┤
│ • Wycena projektu (assembly) — BAZOWA       │
│ • Usługi (service_order) — dołączone        │
│ [GiB Lab info: wykorzystanie 94%, odpady...]│
│                                             │
└─────────────────────────────────────────────┘
```

### Reguła #9: Koloryzacja/oznaczenia źródeł

```css
/* assembly / quick_quote / import_3d = NIEBIESKI (bazowy) */
.pricing-base { color: #1e40af; font-weight: bold; }

/* services = ZIELONY (dołączany) */
.pricing-supplement { color: #059669; }

/* giblab = ŻÓŁTY (feedback/info tylko) */
.pricing-metadata { color: #d97706; font-weight: normal; }
```

### Reguła #10: Ostrzeżenia w UI

```python
# Jeśli istnieje ryzyko, pokaż warning:

if len(base_models) > 1:
    warning = "⚠️ Wiele źródeł bazowych! " \
              "Mogą być liczone podwójnie. " \
              "Potwierdź że to celowe."
    show_warning_dialog(warning)

if user_switched_tabs_with_unsaved():
    info = "ℹ️ Zmieniono źródło bazowe wyceny. " \
           "Poprzednia wycena nie będzie liczona."
    show_info_banner(info)
```

---

## 7. KONTEKST BIZNESOWY — JAK TO DECYDUJEMY

### Reguła #11: Zarządzanie kontekstem

```python
class QuoteContext:
    """Określa który projekt / wycena jest teraz aktywny"""

    base_source: str  # 'assembly' | 'quick_quote' | 'import_3d'
    client_name: str
    order_code: str
    created_at: str

    def switched_base_source(self, new_source: str) -> bool:
        """
        Czy zmieniliśmy źródło bazowe?
        Jeśli TAK:
        - Stara wycena jest zignorowana
        - Nowa wycena staje się bazową
        - Usługi mogą być ponownie dodane do nowego bazowego
        """
        return self.base_source != new_source
```

### Reguła #12: Persistence — kiedy zapisywać merge

```
Nie zapisuj merge'a automatycznie!

Scenariusze zapisu (Etap 4 — future):

1. User w [Podsumowanie] kliknie "Zapisz wycenę"
   → Zapisz merged model (wraz z informacją które źródła użyto)

2. User przełączy źródło bazowe
   → Pytaj: "Zapisać starą wycenę? Czy zrezygnować?"

3. User doda usługę / zmieni parametry
   → Brudna kopja (dirty flag) do następnego zapisu
```

---

## 8. TABELA DECYZYJNA — MERGE ALLOWED?

| Scenariusz | Base | Services | GiB Lab | Merge? | Uwagi |
|-----------|------|----------|---------|--------|-------|
| assembly tylko | ✓ | — | — | ✅ YES | Czysty case |
| assembly + svc | ✓ | ✓ | — | ✅ YES | svc doliczane |
| assembly + gib | ✓ | — | ✓ | ✅ YES | gib = meta tylko |
| assembly + svc + gib | ✓ | ✓ | ✓ | ✅ YES | Wszystkie safe |
| quick_quote tylko | ✓ | — | — | ✅ YES | Czysty case |
| quick_quote + svc | ✓ | ✓ | — | ✅ YES | svc doliczane |
| import_3d tylko | ✓ | — | — | ✅ YES | Czysty case |
| import_3d + svc | ✓ | ✓ | — | ✅ YES | svc doliczane |
| import_3d + gib | ✓ | — | ✓ | ✅ YES | gib = meta |
| assembly + quick | ✓ | — | — | ❌ NO | 2 bazy! |
| assembly + import | ✓ | — | — | ❌ NO | 2 bazy! |
| svc + svc | ✓ | ✓ | — | ❌ NO | 2 svc! |
| gib tylko | — | — | ✓ | ❌ NO | Brak bazy! |

---

## 9. PODSUMOWANIE — CO MUSIMY ZROBIĆ

### Teraz (Etap 3 — już zrobione)
- ✓ Providers dla każdego źródła
- ✓ merge_project_models() dla różnych kombinacji
- ✓ UnifiedSummaryPanel wyświetla dane

### Następnie (Etap 4 — wymagane przed save)
- Dodać `validate_merge()` safety checks
- Implementować warning'i w UI
- Koloryzować źródła danych
- Zablokować niebezpieczne merge'i

### Etap 5+ (future)
- Zapisywanie merged model'i
- Porównanie wycen (dla 2+ baz)
- Tracking zmian w audit trail

---

## 10. ZATWIERDZENIE

**Status Draft**: Wymaga potwierdzenia przed implementacją safety guards

**Pytania do zatwierdzenia**:

1. ✓ / ❌ — Czy źródła bazowe powinny być autoswitching (oparty na aktywnej tab)?
2. ✓ / ❌ — Czy usługi mogą być dodane do każdego źródła bazowego?
3. ✓ / ❌ — Czy GiB Lab powinno być NIGDY wliczane w ceny?
4. ✓ / ❌ — Czy merge bez jawnej zgody powinien być blokowany (dla 2+ baz)?
5. ✓ / ❌ — Czy koloryzacja źródeł jest wystarczająca do UI safety?

---
