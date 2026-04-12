# TECH_modul - pakiet dla ChatGPT

Ten plik jest przygotowany jako jeden, spójny kontekst dla analizy struktury programu i wygladu UI.
Najlepiej wkleic go razem z zalaczonymi screenami albo otworzyc w edytorze, ktory renderuje lokalne obrazy.

## Cel pakietu

Chodzi o pokazanie:
1. jak wyglada i z czego sklada sie aplikacja TECH_modul,
2. jak jest zorganizowana na poziomie zakladek i workflow,
3. jak wyglada sekcja wyceny oraz import z 3D-konstruktora,
4. jak powinny byc czytane ekrany konsultacyjne przez model AI.

## Sposob uruchomienia

- Start aplikacji: `C:\PythonProject\TECH_modul\START_TECH_MODUL_GUI.bat`
- Entry point: `C:\PythonProject\TECH_modul\src\app\main.py`
- Glowne okno: `C:\PythonProject\TECH_modul\src\app\main_window.py`

## Struktura aplikacji

### Warstwa startowa
- `src/app/main.py`
- `src/app/main_window.py`
- `src/app/navigation_groups.py`
- `src/tabs/registry.py`

### Najwazniejsze zakladki uzytkowe
- `Start`
- `Zamowienie`
- `Wycena`
- `sekcja do wyceny`
- `Wycena (3DConstructor)`
- `Modul`
- `Komplet`
- `Sciana`
- `Bazy`

### Obszary powiazane z importem i wycena
- `src/tabs/sekcja_do_wyceny/tab_sekcja_do_wyceny.py`
- `src/tabs/wycena/dialog_import_3dc.py`
- `src/tabs/szybka_wycena/tab_szybka_wycena.py`
- `src/services/constructor_3dc_quote_import_service.py`
- `src/storage/constructor_3dc_mapping_store_json.py`

## Jak czytac interfejs

### 1. Gorny pasek aplikacji
To jest glowna nawigacja miedzy obszarami programu. Nie jest to pojedynczy ekran, tylko caly system pracy:
- sprzedaż,
- wyceny,
- projekty,
- bazy,
- ustawienia i inne narzedzia.

### 2. Sekcja wyceny
To jest miejsce pracy dla szybkiej wyceny i importu z 3D-konstruktora.

### 3. Wycena 3DConstructor
To osobny workflow z podzialem na etapy:
- import,
- kontrola,
- mapowanie,
- wycena,
- rozkroj.

## Co model ma zwrocic uwage

1. Czy UI jest czytelne dla nietechnicznego uzytkownika.
2. Czy widac rozdzial miedzy:
   - importem,
   - kontrola danych,
   - mapowaniem,
   - wycena,
   - rozkrojem.
3. Czy tabele sa rzeczywiscie „excelowe”, a nie tylko dekoracyjne.
4. Czy z interfejsu da sie wyczytac, skad bierze sie cena i z czego sklada sie pozycja.
5. Czy nie ma jednego dlugiego widoku wymagajacego ciaglego scrollowania.

## Kluczowe ekrany

### 1. Aktualny wyglad sekcji szybkiej wyceny

Ten screen pokazuje obecny rozklad sekcji, tabele pozycji i tabele rozliczeniowa.
To jest wazne, bo na tej bazie uzytkownik oczekuje podobnej przejrzystosci w nowych widokach.

![Screenshot 66](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_66.png)

### 2. Docelowy mockup importu i wyceny - widok importu

To jest wzor, jak ma wygladac import oraz tabela kontroli:
- podglad,
- statusy,
- tabela danych,
- panel boczny.

![Screenshot 67](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_67.png)

### 3. Docelowy mockup - tabela wyceny po imporcie

To jest wzor tabeli rozliczeniowej:
- pozycje,
- zrodlo,
- koszt materialu,
- koszt okleiny,
- robocizna,
- suma.

![Screenshot 68](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_68.png)

### 4. Docelowy mockup - mapowanie materialow

To jest wzor podzakladki mapowania:
- material z importu,
- nasz material,
- status,
- akcje po prawej.

![Screenshot 69](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_69.png)

### 5. Docelowy mockup - kompletna kompozycja workflow

Ten screen pokazuje caly kierunek wizualny:
- jasne karty,
- kafelki KPI,
- segmentowe kroki,
- czytelny podzial na etapy.

![Screenshot 70](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_70.png)

### 6. Aktualny widok zakladki Wycena (3DConstructor)

Ten screen pokazuje aktualny stan zakladki w aplikacji i to, co bylo problemem UX:
- za duzo jednego widoku,
- za duzo pionowego scrolla,
- brak podzielenia na etapy.

![Screenshot 74](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_74.png)

## Co jest wazne funkcjonalnie

### Import z 3D-konstruktora
- plik `.project` jest czytany lokalnie,
- program rozpoznaje sekcje typu formatka, front, okucie, lacznik, operacja,
- dane trafiaja do kontroli i wyceny.

### Mapowanie
- nazwy z importu moga byc inne niz w lokalnej bazie,
- mapowanie ma byc trwałe i widoczne,
- uzytkownik ma widziec status rozpoznania.

### Wycena
- tabela ma pokazac sklad kosztu,
- model powinien widziec rozbicie po kolumnach,
- suma pozycji ma byc czytelna.

### Rozkroj
- osobny etap dla danych realnych,
- ma pokazywac roznice miedzy teoria a zakupem realnym.

## Zasady dla modelu

- Oceniaj najpierw strukture i czytelnosc.
- Nie zakladaj, ze wszystko ma byc na jednym ekranie.
- Zwracaj uwage na to, czy workflow etapowy jest jasny.
- Porownuj mockup z aktualnym kodem i screenami.
- Jesli widzisz, ze cos jest niewidoczne lub zbyt schowane, traktuj to jako problem.

## Minimalna instrukcja dla ChatGPT

Jeśli ten plik ma byc uzyty jako prompt, to warto dopisac:

> Przeanalizuj dolaczony pakiet screenow i strukturę programu TECH_modul. Opisz, jak jest zbudowany workflow wyceny i importu 3D-konstruktora, wskaz miejsca, gdzie UI jest czytelne, a gdzie wymaga poprawy. Priorytetem sa: podzial na etapy, czytelnosc tabel i widocznosc kosztu.

## Dodatkowe pliki pomocnicze

- `C:\PythonProject\TECH_modul\docs\consultation_pack\README_PL.md`
- `C:\PythonProject\TECH_modul\docs\consultation_pack\SCREENS_FULL_INDEX.md`
- `C:\PythonProject\TECH_modul\docs\architecture.md`
- `C:\PythonProject\TECH_modul\README.md`
