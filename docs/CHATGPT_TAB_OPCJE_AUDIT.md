# CHATGPT_TAB_OPCJE_AUDIT.md
# Stan zakładki "Opcje" w CAD Web — co działa, co nie działa, co robić
# Projekt: TECH_modul — ERP dla stolarni meblowej
# Data: 2026-04-23

---

## Kontekst ogólny

Aplikacja ma dwie nakładające się wersje edytora modułów:
- **Desktop** (PyQt6) — pełny, produkcyjny edytor modułów w `src/tabs/modul/tab_modul.py`
- **Web CAD** (Next.js) — rozwijany edytor w `frontend/src/app/configuration/page.tsx`

Zrzut ekranu pokazuje **Web CAD** pod adresem `/configuration`.
Tytuł paska: `TECH MODUL 2.0 (CAD DEVELOPMENT MODE)`.

---

## Struktura strony `/configuration`

```
┌──────────────────────────────────────────────────────────┐
│  TOPBAR: MODUŁ / SCENA | Odśwież | Zastosuj | Moduł/Scena│
├──────────┬───────────────────────────────┬───────────────┤
│ LEWY     │ CENTRUM                       │ PRAWY         │
│ PANEL    │ 3D Canvas (Module3DViewer)    │ BOM TABLE     │
│ 340px    │ React Three Fiber / Three.js  │ 450px         │
│          │                               │               │
│ Tabs:    │ ← CAŁKOWICIE CZARNY           │ ← PUSTY       │
│ Główne   │                               │               │
│ Opcje    │                               │               │
│ Okucia   │                               │               │
│ Ustawienia│                              │               │
│ CAM      │                               │               │
└──────────┴───────────────────────────────┴───────────────┘
```

---

## Zakładka "Opcje" — co zawiera

**Plik:** `frontend/src/app/configuration/page.tsx` (linie 717–801)
**Stan aktywacji:** `activeTab === "options"`

Sekcje i pola:

### KONSTRUKCJA
| Pole | Klucz API | Typ |
|---|---|---|
| Złącza Korpusu | `carcass_joint_type` | select: type2/minifix/confirmat/clamex |
| Montaż Pleców | `back_mounting_mode` | select: overlay/insert/recess/recess_service |

### WNĘTRZE
| Pole | Klucz API | Typ |
|---|---|---|
| Półki (szt) | `shelf_count` | number input |
| Przegrody (szt) | `divider_count` | number input |

### NÓŻKI I COKÓŁ
| Pole | Klucz API | Typ |
|---|---|---|
| Cokół (Plinth) | `has_plinth` | checkbox |
| Wysokość Nóżki | `legs_height_mm` | number input |
| Cofnięcie Cokołu | `plinth_inset_mm` | number input (disabled gdy !has_plinth) |
| Odsunięcie Przód | `leg_offset_front` | number input |
| Odsunięcie Tył | `leg_offset_back` | number input |
| Odsunięcie Boki | `leg_offset_side` | number input |

---

## Co DZIAŁA w zakładce Opcje

### ✅ Pola formularza — backend obsługuje

Każde pole wywołuje `updateProperty(key, value)` → `TechModulAPI.applyModuleOperation()`
→ `POST /api/operations/apply` z akcją `module.update_properties`.

**Potwierdzenie w backendzie** (`src/domain/operations/module_ops.py`, linia ~754):
```python
"shelf_count", "divider_count", "drawer_count",
"carcass_top_mode", "carcass_bottom_mode", "back_mounting_mode",
"carcass_joint_type", "leg_type", "legs_height_mm",
"leg_offset_front", "leg_offset_back", "leg_offset_side",
"has_plinth", "plinth_height_mm", "plinth_inset_mm",
```

**Wszystkie pola z zakładki Opcje są na tej liście** — backend je obsługuje.

### ✅ Po zmianie — odświeżenie modułu

Po `updateProperty()` wywoływane jest `load()` → `getProjectModules()` → lista modułów
jest odświeżana. Pole `selectedModule` dostaje nowe wartości.

---

## Co NIE DZIAŁA

### ❌ 1. Czarny canvas 3D — krytyczny problem

**Komponent:** `frontend/src/components/Module3DViewer.tsx`
**Biblioteka:** React Three Fiber + Three.js + `@react-three/drei`

Canvas jest całkowicie czarny. Trzy pewne przyczyny i jedna krytyczna:

#### Przyczyna A: Brak pliku czcionki — CRASH Canvas

```tsx
// Module3DViewer.tsx — linia ~450, 492, 552
<Text fontSize={0.045} color="#ffffff" font="/fonts/Inter-Black.woff">
```

Komponent `Text` z `@react-three/drei` próbuje załadować czcionkę z:
```
/fonts/Inter-Black.woff
```

**Plik nie istnieje:**
```
frontend/public/fonts/  ← katalog jest PUSTY (glob nie znalazł żadnych plików)
```

Gdy `Text` nie może załadować czcionki, wyrzuca błąd wewnątrz Canvas (bez
`<ErrorBoundary>`), który zatrzymuje cały render Three.js → czarny ekran.

#### Przyczyna B: Warunkowe wywołanie hooka — Rules of Hooks violation

```tsx
// BoxModule component — linia ~273
const texture = textureUrl ? useTexture(textureUrl) : null;
```

`useTexture` jest hookiem React — nie może być wywoływany warunkowo.
Jeśli `textureUrl` jest `undefined` (brak faktury materiału), hook NIE jest
wywoływany. Przy następnym renderze z `textureUrl !== undefined`, React zgłosi
błąd "Rendered fewer hooks than expected" → crash.

#### Przyczyna C: `Environment preset="studio"` może nie załadować

```tsx
<Environment preset="studio" />
```

`@react-three/drei` pobiera środowisko HDR z CDN lub lokalnego folderu.
Bez połączenia z siecią lub bez pliku lokalnego, ładowanie może się nie powieść.
Scena nie będzie miała environment mapy, ale nie powinno to całkowicie blokować
renderowania — to mniejszy problem.

#### Skutek

Czarny canvas oznacza, że ŻADNA zmiana w Opcjach (półki, nóżki, złącza)
nie jest widoczna wizualnie, nawet jeśli backend zapisuje dane poprawnie.

---

### ❌ 2. BOM table (ZESTAWIENIE FORMATEK) — pusta

**Lokalizacja:** prawa kolumna strony, linia ~1016

```tsx
{selectedModule?.parts && Object.values(selectedModule.parts).length > 0
  ? ... // renderuje wiersze
  : <tr><td>Brak formatek wygenerowanych przez backend.</td></tr>
}
```

Warunek: `selectedModule.parts` musi być wypełnione przez API.

**Łańcuch danych:**
```
GET /api/modules/{id} lub GET /api/projects/{id}/modules
  → musi zwrócić pole "parts" z obliczonymi formatkami
  → parts.id, parts.name_pl, parts.dims_mm.{w, h, t}, parts.material_key
```

**Problem:** `getProjectModules()` zwraca moduły z polami `width/height/depth/name`
ale prawdopodobnie BEZ obliczonych formatek (`parts` jest puste lub null).

BOM w desktopie jest generowany przez reguły w `src/core/rules/` i renderowany
przez `BomBlock` (`src/tabs/modul/bom_block.py`). W wersji web to przeliczanie
nie jest wywoływane po stronie API — endpoint musiałby wywołać `apply_rules()`
dla modułu i zwrócić wynikowe formatki w odpowiedzi.

---

### ❌ 3. Zmiany w Opcjach nie aktualizują 3D natychmiast

`updateProperty("shelf_count", 3)` wywołuje `load()`, który przeładowuje moduły.
Dopiero po przeładowaniu `selectedModule.shelf_count` zmienia się, co powoduje
re-render `Module3DViewer` z nowym `shelfCount` propem.

Problem 1: Canvas jest czarny, więc i tak tego nie widać.
Problem 2: `load()` jest wywoływane po każdym keystroke (brak debounce na inputach).
Wpisanie "100" w pole "Wysokość Nóżki" wywołuje 3 żądania API: dla "1", "10", "100".

---

### ❌ 4. `tab_sciana.py` desktop — brak komunikacji z web

Moduł CNC/nóżki/złącza z "Opcji" webowych są zapisywane do JSON projektu.
Desktop otwiera ten sam projekt, ale synchronizacja (jeśli oba działają jednocześnie)
jest oparta na pliku — nie ma warstwy websocket ani powiadomień.

---

## Zestawienie: Co jest zrobione, co brakuje

| Komponent | Stan | Notatka |
|---|---|---|
| Zakładka Opcje — UI | ✅ Pełna | Wszystkie pola wyrenderowane |
| Zakładka Opcje — API | ✅ Pełna | Backend obsługuje wszystkie klucze |
| Zakładka Opcje — zapis | ✅ Działa | updateProperty → module.update_properties |
| 3D Canvas render | ❌ Czarny | Brak czcionki / conditional hook / crash |
| BOM table data | ❌ Pusta | API nie zwraca parts z formatkami |
| Debounce na inputach | ❌ Brak | Każdy keystroke = jedno API call |
| Wizualna odpowiedź na Opcje | ❌ Brak | Canvas czarny, BOM pusty |
| Synchronizacja desk↔web | ⚠️ Plik | Działa przez plik JSON, bez live sync |

---

## Co trzeba zrobić — priorytety

### Priorytet 1: Napraw czarny canvas (Quick wins)

**A. Dodaj czcionkę lub usuń `font=` z `Text`**

Opcja 1 — usuń prop `font` (wtedy drei użyje domyślnej czcionki):
```tsx
// Przed:
<Text fontSize={0.045} color="#ffffff" font="/fonts/Inter-Black.woff">
// Po:
<Text fontSize={0.045} color="#ffffff">
```

Opcja 2 — pobierz czcionkę Inter i umieść w `frontend/public/fonts/Inter-Black.woff`

**B. Napraw conditional hook**

```tsx
// Przed (BŁĘDNE):
const texture = textureUrl ? useTexture(textureUrl) : null;

// Po (poprawne):
const texture = useTexture(textureUrl || "");
// lub jeśli chcesz unikać pustego URL-a:
// przenieś useTexture do osobnego komponentu TexturedBoard
```

**C. Dodaj ErrorBoundary wokół Canvas**

```tsx
<ErrorBoundary fallback={<div className="text-red-400">Błąd 3D</div>}>
  <Canvas ...>
    ...
  </Canvas>
</ErrorBoundary>
```

Bez ErrorBoundary każdy crash w Three.js nie jest logowany w UI.

---

### Priorytet 2: Wypełnij BOM table

API endpoint `GET /api/projects/{id}/modules` lub `GET /api/modules/{id}`
musi zwracać pole `parts` z obliczonymi formatkami.

W backendzie formatki są przeliczane przez `apply_module_rules()` w
`src/core/rules/`. Należy to wywołać podczas serializacji modułu do API.

Minimalna struktura każdego `part`:
```json
{
  "id": "side_left",
  "name_pl": "Bok lewy",
  "dims_mm": { "w": 540, "h": 720, "t": 18 },
  "material_key": "mdf_18",
  "edge_banding": { "left": "abs_22" }
}
```

---

### Priorytet 3: Dodaj debounce na number inputs

```tsx
// Zamiast:
onChange={(e) => updateProperty("shelf_count", parseInt(e.target.value) || 0)}

// Użyj:
onChange={(e) => {
  const val = parseInt(e.target.value) || 0;
  clearTimeout(debounceRef.current);
  debounceRef.current = setTimeout(() => updateProperty("shelf_count", val), 500);
}}
```

Lub użyj `useDebouncedCallback` z `use-debounce`.

---

### Priorytet 4: Powiąż zmiany Opcji z widokiem 3D

Aktualnie zakładka Opcje nie aktualizuje lokalnych stanów `{w, h, d}`.
Po naprawie canvasa, zmiany `shelf_count` / `legs_height_mm` z Opcji
powinny natychmiast zmieniać wygląd 3D bez potrzeby pełnego reload.

Wymaga to: po `updateProperty()` pobrania nowego `selectedModule` i
aktualizacji propsów do `Module3DViewer`.

---

## Pliki kluczowe

| Plik | Rola |
|---|---|
| `frontend/src/app/configuration/page.tsx` | Cała strona CAD, zakładka Opcje linie 717–801 |
| `frontend/src/components/Module3DViewer.tsx` | Komponent 3D (czarny canvas) |
| `frontend/public/fonts/` | TU BRAKUJE Inter-Black.woff |
| `src/domain/operations/module_ops.py` | Backend — obsługuje update_properties |
| `src/api/main_api.py` | Endpointy API dla modułów |

---

## Skrócone podsumowanie dla ChatGPT

> Zakładka "Opcje" w webowym edytorze CAD (`/configuration`, komponent
> `frontend/src/app/configuration/page.tsx`) ma wszystkie pola formularza
> poprawnie podłączone do backendu — zapis działa.
>
> Problem 1 (krytyczny): Środkowy panel 3D (`Module3DViewer.tsx`)
> jest całkowicie czarny. Główna przyczyna: komponent `<Text>` z
> `@react-three/drei` szuka czcionki `/fonts/Inter-Black.woff`, której
> nie ma w `frontend/public/fonts/` (katalog jest pusty). Crash jest
> cichy (brak ErrorBoundary), więc canvas renderuje się jako czarny div.
> Dodatkowy problem: warunkowe wywołanie hooka `useTexture` narusza
> Rules of Hooks.
>
> Problem 2: Prawa kolumna (BOM — ZESTAWIENIE FORMATEK) jest pusta
> ponieważ API nie zwraca pola `parts` z przeliczonymi formatkami.
>
> Fix 1 (15 minut): usuń `font="/fonts/Inter-Black.woff"` z `<Text>`
> lub dostarcz plik czcionki. Następnie przenieś `useTexture` do
> osobnego komponentu.
>
> Fix 2 (kilka godzin): endpoint API modułów musi wywołać
> `apply_module_rules()` i zwrócić pole `parts` w odpowiedzi JSON.

---

*Koniec dokumentu. Wygenerowano na podstawie audytu kodu: 2026-04-23*
