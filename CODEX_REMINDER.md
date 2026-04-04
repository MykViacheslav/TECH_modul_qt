CODEX REVIEW AND ROADMAP

Date: 2026-03-29

Summary: Per-wkladka reviews with concrete improvements and patch plans. This file is intended to guide incremental changes to the UI, data model, and tests, and to serve as a reference for future work in the CODEX tab.

1) Wkładka: USŁUGI
- Stan obecny:
  - Kolejność zakładek: Nowa USLUGA → BAZA USLUG → Klijenty → Cen nik (Cennik)
  - Edytor cenika obsługuje składniki, które mogą być materiałami z bazy, pracą (czas) i innymi usługami z cennika.
- Główne problemy:
  - Wybór materiału może prowadzić do niejasności, jeśli wyświetlany jest tylko typ (np. 'korpus') bez kontekstu nazwy materiału.
  - Brak niektórych pól identyfikujących (np. brakuje standardowych identyfikatorów dla niektórych składników) i spójności ID w bazie materiałów.
- Rekomendacje (Po kolei):
  1) Wprowadzić filtr typów materiałów nad listą materiałów w BAZA МATERIALU (np. dropdown: korpus, front, plecy, okleina, okucie, plyta, profil, lakier) i filtrować listę po wybranym typie.
  2) W ceniku wyświetlać zarówno typ, jak i nazwę materiału w polach: sumaryzować nazwy i identyfikatory (np. nazwa (id)) w dropdownach składników.
  3) Dbać o spójność identyfikatorów materiałów (M000x) – ensure that wszystkie materiały w bazie mają unikalne ID.
  4) W modelu składników dodać niezależne walidacje: typ/kod, ref_id, nazwa, ilość, jednostka, koszt_szac., etc.
  5) Dodać cross-tab signals: gdy składnik w ceniku się zmienia, zaktualizować wartość w kalkulacji ceny i ewentualnie dashboard.
- Plan patchy (przykładowe diff-y):
  - patch 1: UI – dodanie filtra Typów materiałów nad Baza materiałów; aktualizacja widoku kolumny Typ na materiałach.
  - patch 2: Cennik – upewnienie, że składniki wybierane z bazy materiałów wyglądają jako Nazwa (ID).
  - patch 3: Model – w ServiceComponentDef i ServiceComponentStoreJson dodać walidacje i identyfikatory jeśli brakuje.
  - patch 4: Testy – dodać UI regression testy dla edytora składników i testy end-to-end dla przepływu.

2) Wkładka: BAZA USŁUG / Baza materiałów
- Problem:
  - Brak jednoznacznej segregacji materiałów po typie, a interfejs do wyboru typu nie był jasno oznaczony.
- Propozycje:
  - Od siebie: w bazie materiałów dodać pole typ (dobrze: jeden z fixture-ów: Korpus, Front, Plecy, Okleina, Okucie, Plywood...).
  - W UI: w Baza materiałów dodać filtr typu ( dropdown ) i wyświetlać materiał nazwą i typem w tabeli: Typ – Nazwa.
  - Zaimplementować mechanizm automatycznego tworzenia grup materiałowych w zależności od typu.

3) Wkładka: KLIENTY
- Co zrobić:
  - Dodać Status klienta i ewentualne powiązanie z zamówieniem (NOWY, W TRAKCIE, ZAKOŃczONE).
  - Dodać raportowanie do dashboardu (ilość aktywnych klientów, średnia wartość zamówień).
  - Integracja z modułem zamówień: kliknięcie na klienta otwiera kontekst zamówień.

4) Wkładka: CENNIK
- Co zrobić:
  - Edytor składników: oddzielić koszty materiałowe od kosztów pracy (dwie kolumny w widoku) i wyświetlać wartości w jednej pozycji.
  - Pokazywać jasno, skąd pochodzą koszty (materiały z bazy vs praca). To może wymagać dodania atrybutu source_type (material/work/service).
  - Zapewnić, że nazwa w oknie edycji skł. z Material z bazy materiałów jest czytelna (nazwa + id) zamiast samego typu.

5) Wkładka: CODEX
- Cel: Zapis recenzji i planu w jednym miejscu i łatwe jej utrzymanie.
- Proponowana forma: plik CODEX_REMINDER.md (zawiera recenzję, plan patchy i testy). Opcjonalnie można wprowadzić w UI tab CODEX, aby mieć jeden dostępny do przeglądania.
- Akcja: wygenerować plik CODEX_REMINDER.md i dodać patch, aby kod mógł wyświetlać treść w interfejsie (np. w TabCodex).

Uwagi końcowe
- Zalecam podejście iteracyjne: najpierw dodać filtr typów w BAZA MATERIALU i poprawić wyświetlanie w wierszach (ID i nazwy), potem dopiąć patch w CENNIK (dwukolumnowy koszt) i wreszcie dodać 5-dostawców do dashboardu, a na koniec testy end-to-end i CODEX.

Zapisane jako CODEX_REMINDER.md.
