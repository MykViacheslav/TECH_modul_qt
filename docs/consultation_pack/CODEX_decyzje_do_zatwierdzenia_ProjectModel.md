# Decyzje Do Zatwierdzenia
## TECH_modul / MSI modul
## Temat: architektura danych po uporzadkowaniu nawigacji i huba `Wycena`

### Cel dokumentu
Ten dokument nie sluzy do wdrozenia.
Ma potwierdzic glówne decyzje architektoniczne przed rozpoczeciem prac nad wspólnym modelem projektu.

---

## 1. Czy tworzymy wspólny `ProjectModel`?
### Decyzja proponowana:
**TAK**

### Uzasadnienie:
Dzis dane projektu, wyceny, uslug i importu 3D sa rozproszone miedzy wieloma modelami i JSON-ami.
Potrzebny jest jeden wspólny rdzen danych projektu, który bedzie spajal:
- wycene projektu,
- szybka wycene,
- import 3D,
- uslugi,
- wynik rozkroju / GiB Lab.

---

## 2. Czy `.project` ma byc zrodlem prawdy w aplikacji?
### Decyzja proponowana:
**NIE**

### Uzasadnienie:
`.project` ma zostac:
- formatem wejscia / wyjscia,
- adapterem integracji z 3DConstructor i GiB Lab,
- plikiem glównym dla uzytkownika,

ale nie powinien byc wewnetrznym rdzeniem modelu aplikacji.

**ProjectModel ma byc wewnetrznym zródlem prawdy aplikacji, ale nie ma zastepowac uzytkownikowi pliku `.project`, który pozostaje glównym plikiem wymiany i pracy z narzedziami zewnetrznymi.**

### Zasada:
- dla uzytkownika: `.project` = glówny plik projektu,
- dla aplikacji: `ProjectModel` = zródlo prawdy.

---

## 3. Czy stare JSON-y zostaja przejsciowo?
### Decyzja proponowana:
**TAK**

### Uzasadnienie:
Obecne JSON-y powinny zostac na czas migracji jako:
- warstwa trwalosci,
- zródla odczytu,
- adaptery,
- fallback bezpieczenstwa.

Nie nalezy usuwac ich od razu.

---

## 4. Czy migracja ma isc najpierw przez adaptery read-only?
### Decyzja proponowana:
**TAK**

### Uzasadnienie:
Najbezpieczniejsza kolejnosc to:
1. odczyt obecnych danych do nowego modelu,
2. porównanie wyników,
3. dopiero pózniej zapis,
4. na koncu wylaczenie starych sciezek.

To ogranicza ryzyko rozjazdu danych i blednych sum.

---

## 5. Czy koncowa wycena ma miec wspólny format pozycji?
### Decyzja proponowana:
**TAK**

### Uzasadnienie:
Niezaleznie od zródla, koncowe pozycje wyceny powinny miec wspólny kontrakt, np.:
- zródlo pozycji,
- grupa,
- nazwa,
- ilosc,
- jednostka,
- material,
- wartosc netto,
- wartosc brutto,
- status,
- dokladnosc / typ pozycji.

### Przykładowa nazwa warstwy:
`quote_lines`

### Zródla pozycji:
- wycena projektu,
- szybka wycena,
- import 3D,
- uslugi,
- korekty po GiB Lab.

---

## 6. Czy `ProjectModel` ma byc jedna wielka klasa?
### Decyzja proponowana:
**NIE**

### Uzasadnienie:
`ProjectModel` powinien byc agregatem nadrzednym zlozonym z mniejszych sekcji, np.:
- `header`
- `quote_context`
- `assemblies`
- `quick_quote`
- `services`
- `import_3d`
- `mapping`
- `giblab_result`
- `pricing_snapshot`

Czyli:
- jeden rdzen,
- ale nie jeden ogromny model z przypadkowymi polami.

---

## 7. Czy stare modele domenowe kopiujemy 1:1 do nowego modelu?
### Decyzja proponowana:
**NIE**

### Uzasadnienie:
Modele takie jak:
- `OrderDef`
- `FurnitureAssemblyDef`
- `ServiceOrderDef`
- `ImportProjectSummary`

nie powinny byc mechanicznie wsadzane do `ProjectModel`.

Zamiast tego:
- trzeba je mapowac przez adaptery,
- a `ProjectModel` ma miec wlasny prosty kontrakt.

---

## 8. Czy wynik GiB Lab ma byc osobnym swiatem poza projektem?
### Decyzja proponowana:
**NIE**

### Uzasadnienie:
Wynik GiB Lab powinien byc czescia projektu, jako osobna sekcja:
- wynik rozkroju,
- liczba plyt,
- odpad,
- resztówki,
- realne zuzycie materialu.

### Zasada:
GiB Lab nie zastepuje projektu.
GiB Lab dostarcza wynik do projektu.

---

## 9. Od którego obszaru zaczynamy pierwszy zapis do nowego modelu?
### Decyzja proponowana:
**od prostszego obszaru, nie od pelnej `Wycena projektu`**

### Rekomendacja:
zaczac od:
- `Uslugi`
albo
- `Szybka wycena`

### Uzasadnienie:
To sa obszary:
- prostsze,
- bardziej izolowane,
- mniej ryzykowne niz pelna wycena kompletów / modulów / scian.

---

## 10. Czy `Wycena projektu` i `Szybka wycena` maja zostac biznesowo odrebne?
### Decyzja proponowana:
**TAK**

### Uzasadnienie:
To sa dwa rózne tryby pracy:
- `Wycena projektu` = tryb systemowy / techniczny,
- `Szybka wycena` = tryb handlowy / orientacyjny.

Nie nalezy ich agresywnie scalac biznesowo.
Mozna je spiac jednym modelem danych i wspólnym podsumowaniem, ale trzeba zachowac ich odrebnosc funkcjonalna.

---

## 11. Czy `Uslugi` maja byc czescia koncowej sumy projektu?
### Decyzja proponowana:
**TAK**

### Uzasadnienie:
Uslugi sa juz dzis elementem koncowego kosztu.
Migracja musi zachowac to 1:1.
Uslugi maja byc widoczne:
- jako osobna grupa w wycenie,
- jako czesc koncowego `Podsumowania`.

---

## 12. Czy najpierw zamykamy architekture, czy dalej poprawiamy UI?
### Decyzja proponowana:
**architektura danych jest nastepnym krokiem**

### Uzasadnienie:
Hub `Wycena` i nawigacja sa juz wystarczajaco uporzadkowane na poziomie UX.
Nie ma potrzeby dalszego kosmetycznego polishu przed decyzjami architektonicznymi.

---

# ZATWIERDZONA KOLEJNOSC DALSZYCH PRAC

## Etap A
Definicja kontraktu `ProjectModel`

## Etap B
Adaptery read-only z obecnych store'ów i JSON-ów

## Etap C
Pierwszy ekran / snapshot tylko do odczytu z nowego modelu

## Etap D
Pierwszy zapis do nowego modelu:
- najpierw `Uslugi` albo `Szybka wycena`

## Etap E
Kolejne obszary:
- `Wycena projektu`
- `Import 3D`
- `Rozkroj / GiB Lab`

## Etap F
Wylaczenie starych sciezek zapisu po stabilizacji

---

# KONSEKWENCJA DECYZJI

Jesli te decyzje zostana zatwierdzone, nastepnym krokiem ma byc:
- przygotowanie formalnej specyfikacji `ProjectModel`,
- wskazanie plików do adapterów read-only,
- rozpisanie pierwszego bezpiecznego wdrozenia bez migracji danych.

Na tym etapie:
- nie wdrazac jeszcze `ProjectModel`,
- nie migrowac danych,
- nie ruszac `.project`,
- nie zmieniac GiB Lab.

Najpierw: kontrakt, adaptery, plan.

Koniec dokumentu.
