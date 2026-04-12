# TECH_modul / MSI modul
## Finanse: checkpoint i specyfikacja etapu przed implementacja

Data: 2026-04-11  
Status: dokument decyzji i architektury (bez wdrozenia pelnej zakladki `Finanse`)

## 1) Checkpoint obecnych zmian

### 1.1 Ustalona mapa programu
- `Start`
- `Zamowienie`
- `Projekt`
- `Wycena`
- `Finanse`
- `Firma`
- `Bazy`
- `Ustawienia`

### 1.2 Ustalone podobszary
- `Projekt`: `Modul`, `Komplet`, `Sciana`
- `Wycena`: `Wycena projektu`, `Szybka wycena`, `Import 3D`, `Uslugi`, `Rozkroj`, `Podsumowanie`
- `Bazy`: `Baza modulow`, `Baza materialow`, `Baza uslug`, `Baza szybkich wycen`
- `Firma`: `Dashboard`, `Alarmy`, `Kalendarz`, `Czas pracy`, `Pracownicy`, `Zakupy`

### 1.3 Ustalenia funkcjonalne z dzisiaj
- `Wycena` zostaje jako hub.
- `Uslugi` sa czescia `Wycena`.
- `Baza uslug` zostaje w `Bazy`.
- `ProjectModel` funkcjonuje jako read-only snapshot.
- Na tym etapie nie ruszamy jeszcze zapisow, JSON-ow, `.project` i GiB Lab.
- `Nowe zamowienie` zostaje krokowe (`N1..N5`).
- `Modul`: kierunek CAD-like, bez naruszania silnika i logiki domenowej.

### 1.4 Aktualny stan repo (roboczy)
- Repo jest w stanie `dirty` z wieloma modyfikacjami i plikami roboczymi.
- To jest zgodne z trwajacym etapem przebudowy UX i architektury.
- Dokument `Finanse` ma byc etapem decyzyjnym przed rozpoczeciem implementacji.

## 2) Specyfikacja architektury danych `Finanse` (formalna)

### 2.1 Zasady ogolne
- Model finansowy rozdziela:
  - dokument handlowy,
  - pozycje dokumentu,
  - platnosci,
  - ruch pieniezny (ledger),
  - rachunki bankowe i kase gotowkowa,
  - zobowiazania pracownicze.
- Kazdy zapis finansowy ma identyfikator, walute, status, timestamp i audyt (`created_by`, `updated_by`).
- VAT liczony jest per pozycja dokumentu, a nie tylko na poziomie naglowka.

### 2.1.1 Twarda zasada: stale ID techniczne
- Kazdy obiekt i kazda pozycja w systemie musi miec wlasne, niepowtarzalne, stale ID techniczne.
- Dotyczy to co najmniej:
  - projektu,
  - zamowienia,
  - dokumentu,
  - pozycji dokumentu,
  - pozycji wyceny,
  - pozycji uslugi,
  - platnosci,
  - ruchu kasy / rachunku,
  - wynagrodzenia / wyplaty,
  - zalacznika,
  - importu 3D,
  - wyniku GiB Lab.
- Nie wolno opierac relacji danych wylacznie na:
  - nazwie,
  - numerze dokumentu,
  - opisie,
  - kodzie pozycji,
  - nazwie projektu.
- Obowiazkowy rozdzial:
  - `id_techniczne`: stale, unikalne, niezmienne,
  - `numer_lub_kod_biznesowy`: czytelny dla uzytkownika, moze podlegac regurom biznesowym.
- Wszystkie relacje miedzy danymi musza byc realizowane po `id_techniczne`.
- Zasada obowiazuje wspolnie dla: `ProjectModel`, `Finanse`, `Wycena`, `Zamowienie` i dalszych integracji.

### 2.2 Proponowane byty domenowe

#### `FinanceDocument`
- Cel: naglowek dokumentu sprzedaazy/zakupu.
- Kluczowe pola:
  - `document_id`, `document_no`, `document_type` (`sale_invoice`, `sale_receipt`, `purchase_invoice`, `correction`, `other`)
  - `counterparty_id`, `project_id` (nullable), `company_cost_center_id` (nullable)
  - `issue_date`, `due_date`, `currency`, `status` (`draft`, `issued`, `partially_paid`, `paid`, `cancelled`)
  - `net_total`, `vat_total`, `gross_total` (agregaty liczone z pozycji)

#### `FinanceDocumentLine`
- Cel: pojedyncza pozycja dokumentu.
- Kluczowe pola:
  - `line_id`, `document_id`, `line_no`
  - `line_type` (`product`, `service`, `material`, `labor`, `other`)
  - `description`, `quantity`, `unit`, `unit_net_price`
  - `vat_rate` (edytowalna), `net_value`, `vat_value`, `gross_value`
  - `project_id` (nullable), `cost_class` (`project`, `company`)

#### `PaymentAllocation`
- Cel: platnosc i jej podzial na metody.
- Kluczowe pola:
  - `payment_id`, `document_id`, `payment_date`, `currency`
  - `total_amount`
  - `status` (`planned`, `booked`, `reconciled`, `cancelled`)

#### `PaymentSplit`
- Cel: czesciowa platnosc (np. gotowka + przelew).
- Kluczowe pola:
  - `split_id`, `payment_id`
  - `method` (`cash`, `bank_transfer`, `card`, `other`)
  - `amount`
  - `source_account_id` lub `source_cashbox_id`
  - `destination_account_id` lub `destination_cashbox_id`

#### `MoneyLedgerEntry`
- Cel: atomowy ruch pieniedzy (ksiega operacyjna).
- Kluczowe pola:
  - `entry_id`, `entry_type` (`inflow`, `outflow`, `transfer`, `salary`, `advance`, `tax`)
  - `amount`, `currency`, `entry_date`
  - `account_id`/`cashbox_id`
  - `linked_document_id`, `linked_payment_id`, `linked_employee_id` (nullable)
  - `project_id` (nullable), `cost_class` (`project`, `company`)
  - `note`, `source_module`

#### `CompanyBankAccount`
- Cel: rachunki firmowe.
- Kluczowe pola:
  - `account_id`, `name`, `bank_name`, `iban_masked`, `active`

#### `CompanyCashbox`
- Cel: kasa gotowkowa firmy.
- Kluczowe pola:
  - `cashbox_id`, `name`, `active`, `current_balance`

#### `EmployeeSettlement`
- Cel: rozliczenie pracownika.
- Kluczowe pola:
  - `settlement_id`, `employee_id`, `period`
  - `accrued_amount`
  - `paid_bank_amount`
  - `paid_cash_amount`
  - `advance_amount`
  - `balance_amount` (wyliczane)

#### `EmployeeAdvance`
- Cel: zaliczki pracownicze.
- Kluczowe pola:
  - `advance_id`, `employee_id`, `advance_date`, `amount`
  - `source_cashbox_id` lub `source_account_id`
  - `project_id` (nullable), `reason`, `status`

### 2.3 Relacje (minimalny rdzen)
- `FinanceDocument 1..n FinanceDocumentLine`
- `FinanceDocument 1..n PaymentAllocation`
- `PaymentAllocation 1..n PaymentSplit`
- `PaymentSplit -> MoneyLedgerEntry` (1..n technicznie)
- `EmployeeSettlement 1..n EmployeeAdvance` (powiazanie okresowe)
- `MoneyLedgerEntry` moze byc powiazany z `project_id` lub oznaczony jako koszt firmowy.

### 2.4 Kontrakt danych dla etapu 1 (read-first)
- Na etapie pierwszej implementacji `Finanse`:
  - najpierw czytanie i agregacja,
  - ograniczone zapisy transakcyjne,
  - bez migracji historycznej.
- Zalecany format agregatu pod UI:
  - `finance_snapshot`
  - sekcje: `kpi`, `sales`, `costs`, `cashflow`, `salary`, `taxes`, `alerts`.

## 3) Reguly biznesowe `Finanse`

### 3.1 VAT per pozycja dokumentu
- VAT liczony osobno dla kazdej `FinanceDocumentLine`.
- `vat_rate` jest edytowalne recznie na linii.
- Agregaty dokumentu:
  - `net_total = suma(line.net_value)`
  - `vat_total = suma(line.vat_value)`
  - `gross_total = suma(line.gross_value)`
- Dokument moze miec linie z roznymi stawkami VAT.

### 3.2 Platnosc czesciowa i mieszana metoda
- Jedna platnosc moze miec wiele `PaymentSplit`.
- Suma splitow musi rownac sie `PaymentAllocation.total_amount`.
- Dopuszczalne: np. 40% gotowka + 60% przelew.
- Status dokumentu:
  - `issued` -> `partially_paid` po pierwszym rozliczeniu niepelnym,
  - `paid` po osiagnieciu 100% kwoty brutto.

### 3.3 Rachunek firmowy i kasa gotowkowa
- Gotowka od klienta:
  - zawsze ksiegowana do `CompanyCashbox`.
- Z kasy gotowkowej moga wyjsc:
  - zakupy,
  - zaliczki pracownicze,
  - wyplaty gotowkowe,
  - wydatki projektowe.
- Kazdy ruch gotowki i banku tworzy `MoneyLedgerEntry`.

### 3.4 Wynagrodzenia i zaliczki
- Rozdzielone pola:
  - `accrued_amount`,
  - `paid_bank_amount`,
  - `paid_cash_amount`,
  - `advance_amount`,
  - `balance_amount = accrued - paid_bank - paid_cash - advance`.
- Zaliczki sa widoczne osobno i maja wplyw na saldo.

### 3.5 Przypisanie kosztu do projektu albo firmy
- Kazdy koszt/platnosc musi miec klasyfikacje:
  - `cost_class = project` i `project_id != null`, albo
  - `cost_class = company` i `project_id == null`.
- Brak klasyfikacji blokuje finalne zatwierdzenie dokumentu.

## 4) Matryca uprawnien

## 4.1 Role (docelowe)
- `admin`
- `director`
- `finance_manager`
- `finance_viewer`
- `project_manager`
- `worker`

## 4.2 Uprawnienia funkcjonalne
- `finance.tab.view`
- `finance.dashboard.view`
- `finance.documents.view`
- `finance.documents.edit`
- `finance.payments.view`
- `finance.payments.edit`
- `finance.cashbox.view`
- `finance.cashbox.edit`
- `finance.salary.view`
- `finance.salary.edit`
- `finance.taxes.view`
- `finance.taxes.edit`
- `finance.reports.export`

## 4.3 Matryca (propozycja)
- `admin`: wszystkie uprawnienia.
- `director`: pelny podglad + edycja finansow, bez ograniczen operacyjnych.
- `finance_manager`: pelna obsluga dokumentow, platnosci, kasy, podatkow, wynagrodzen.
- `finance_viewer`: tylko podglad `Finanse` i raporty bez edycji.
- `project_manager`: brak tab `Finanse`, moze miec tylko wybrane KPI projektowe bez danych wrazliwych.
- `worker`: brak dostepu do `Finanse` i brak szczegolow finansowych na dashboardzie.

## 4.4 Wymuszenia UI
- Uzytkownik bez `finance.tab.view`:
  - nie widzi zakladki `Finanse`.
- Uzytkownik bez `finance.dashboard.view`:
  - nie widzi widgetow finansowych na dashboardzie.
- Uzytkownik bez `finance.salary.view`:
  - nie widzi sekcji wynagrodzen ani zadnych kwot placowych.

## 5) Mapa UI zakladki `Finanse`

### 5.1 Podzakladki
- `Podsumowanie`
- `Sprzedaz / Przychody`
- `Zakupy i Koszty`
- `Kasa i Rachunki`
- `Wynagrodzenia`
- `Podatki i Rozrachunki`
- `Raporty`

### 5.2 Zawartosc per podzakladka

#### `Podsumowanie`
- KPI: przychod, koszt, marza, saldo bank, saldo kasa, naleznosci, zobowiazania.
- Filtry globalne:
  - okres,
  - projekt / firma,
  - status dokumentu.

#### `Sprzedaz / Przychody`
- Tabela dokumentow sprzedazy.
- Widok pozycji dokumentu (split panel).
- Status platnosci i naleznosci.

#### `Zakupy i Koszty`
- Tabela kosztow zakupu.
- Podzial na koszt projektowy i firmowy.
- Powiazanie z projektem i dostawca.

#### `Kasa i Rachunki`
- Rejestr ruchow pienieznych (`MoneyLedgerEntry`).
- Przelaczniki kont:
  - rachunki bankowe,
  - kasa gotowkowa.
- Operacje transferu miedzy bankiem i kasa.

#### `Wynagrodzenia`
- Lista pracownikow z saldem rozliczenia.
- Szczegoly naliczone / wyplacone / zaliczki / saldo.
- Historia zaliczek.

#### `Podatki i Rozrachunki`
- Zestawienia VAT.
- Naleznosci i zobowiazania wedlug terminu.
- Ostrzezenia o zaleglosciach.

#### `Raporty`
- Raporty okresowe:
  - miesieczne,
  - kwartalne,
  - roczne.
- Eksport CSV/PDF.

### 5.3 Wspolne filtry i UX
- Filtry stale:
  - okres (`od-do`, preset miesiac/kwartal/rok),
  - zakres (`projekt`, `firma`, `wszystko`),
  - waluta,
  - status.
- Sticky header tabel.
- Jeden aktywny obszar roboczy na podzakladke, bez dlugiego scrolla.
- Widoczne informacje „co dalej” i statusy procesowe.

### 5.4 Przeplyw uzytkownika (minimalny)
1. Wejscie do `Finanse` -> `Podsumowanie`.
2. Filtr okresu i zakresu (projekt/firma).
3. Wejscie w `Sprzedaz` lub `Zakupy`.
4. Otworzenie dokumentu -> podglad linii VAT i statusu platnosci.
5. Przejscie do `Kasa i Rachunki` dla weryfikacji realnych przeplywow.
6. Przejscie do `Raporty` i eksport.

## 6) Kolejnosc prac (zatwierdzona)
1. Checkpoint obecnych zmian.
2. Specyfikacja `Finanse`.
3. Reguly biznesowe.
4. Matryca uprawnien.
5. Mapa UI.
6. Dopiero po zatwierdzeniu: kod.

## 7) Zakres wykluczony na tym etapie
- Bez pelnej implementacji `Finanse`.
- Bez migracji danych.
- Bez wspolnego zapisu finansowego.
- Bez zmian w `.project`.
- Bez zmian w GiB Lab.
- Bez glebokiego refaktoru obecnych zapisow.

---
Dokument gotowy jako podstawa do kolejnego etapu: projekt techniczny i wdrozenie iteracyjne `Finanse`.
