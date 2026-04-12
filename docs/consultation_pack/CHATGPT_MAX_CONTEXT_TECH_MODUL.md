# TECH_modul - MAX CONTEXT PACK

To jest pakiet startowy dla ChatGPT do analizy naszej aplikacji desktopowej `TECH_modul`.

Najwazniejsze:
- to jest aplikacja offline-first dla firmy stolarskiej,
- uzytkownik nie jest programista,
- GUI ma byc po polsku,
- klucze techniczne / ID / pola techniczne maja byc po angielsku,
- glowny obszar pracy dla importu 3D i wyceny ma byc zwiazany z `Wycena`,
- przed wdrozeniem model ma najpierw pokazac analize plikow, potem plan, potem wdrozenie.

## Instrukcja dla ChatGPT

Pracuj w tej kolejnosci:
1. Najpierw pokaż analize plikow i aktualnej struktury.
2. Potem zaproponuj plan wdrozenia.
3. Dopiero potem wykonaj zmiany blokowo.

Nie rozwalaj reszty programu. Pracuj minimalnie inwazyjnie.

## Docelowy kierunek UX

Glowny workflow importu 3D, kontroli, mapowania, wyceny i rozkroju ma byc prowadzony wewnatrz obszaru wyceny, etapowo, bez jednego dlugiego scrolla.

Preferowane etapy:
- `Import`
- `Kontrola`
- `Mapowanie`
- `Wycena`
- `Rozkroj`

## Gdzie jest start aplikacji

- `C:\PythonProject\TECH_modul\START_TECH_MODUL_GUI.bat`
- `C:\PythonProject\TECH_modul\src\app\main.py`
- `C:\PythonProject\TECH_modul\src\app\main_window.py`
- `C:\PythonProject\TECH_modul\src\tabs\registry.py`
- `C:\PythonProject\TECH_modul\src\app\navigation_groups.py`

## Kluczowe obszary do analizy

### Nawigacja i glowny UI
- `C:\PythonProject\TECH_modul\src\app\main_window.py`
- `C:\PythonProject\TECH_modul\src\app\navigation_groups.py`
- `C:\PythonProject\TECH_modul\src\tabs\registry.py`

### Wycena i import 3D
- `C:\PythonProject\TECH_modul\src\tabs\wycena\dialog_import_3dc.py`
- `C:\PythonProject\TECH_modul\src\tabs\sekcja_do_wyceny\tab_sekcja_do_wyceny.py`
- `C:\PythonProject\TECH_modul\src\tabs\szybka_wycena\tab_szybka_wycena.py`
- `C:\PythonProject\TECH_modul\src\services\constructor_3dc_quote_import_service.py`
- `C:\PythonProject\TECH_modul\src\storage\constructor_3dc_mapping_store_json.py`

## Glowne zakladki aplikacji

Z punktu widzenia kodu aplikacja ma miedzy innymi te obszary:
- `Start`
- `Nowe zamowienie`
- `Wycena`
- `sekcja do wyceny`
- `Wycena (3DConstructor)`
- `Uslugi`
- `Modul`
- `Komplet`
- `Sciana`
- `Dashboard`
- `ALARMY`
- `Kalendarz`
- `Czas pracy`
- `Wydatki stale firmy`
- `Wydatki zmienne`
- `Pracownik`
- `Zakupy`
- `Bazy`
- `BAZA_modul`
- `Baza materialu`
- `Baza szybkich wycen`
- `Ustawienia`
- `Ekrany`
- `Stanowiska`
- `QR TELEFON`
- `STRUKTURA`

## Co ma byc scalone logicznie

Najwazniejszy obszar pracy:
- `Wycena`

To tam powinien byc prowadzony workflow importu 3D, mapowania, wyceny i przygotowania rozkroju.

Nie nalezy robic osobnych, podobnych glownych zakladek dla jednego workflow bez wyraźnej potrzeby.

## Co model ma ocenic

1. Czy struktura zakladek jest logiczna.
2. Czy workflow importu 3D jest etapowy.
3. Czy tabela kontroli importu jest czytelna.
4. Czy tabela wyceny pokazuje skad bierze sie cena.
5. Czy rozkroj / GiB Lab da sie pokazac jako osobny etap.
6. Czy dashboard da sie uspokoic wizualnie.
7. Czy mozna zmniejszyc chaos na gornym pasku bez psucia innych dzialow.

## Wazne pliki dokumentacji

- `C:\PythonProject\TECH_modul\docs\consultation_pack\README_PL.md`
- `C:\PythonProject\TECH_modul\docs\consultation_pack\CHECKLISTA_WYSYLKI.md`
- `C:\PythonProject\TECH_modul\docs\consultation_pack\KONTEKST_APP_PL.md`
- `C:\PythonProject\TECH_modul\docs\consultation_pack\SCREENS_INDEX.md`
- `C:\PythonProject\TECH_modul\docs\consultation_pack\SCREENS_FULL_INDEX.md`
- `C:\PythonProject\TECH_modul\docs\consultation_pack\PROMPT_04_MEGA_AUDYT_WIZUALNY.txt`

## Zestaw screenow do analizy

### Najwazniejsze screeny z aktualnych zmian

![Screenshot 66](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_66.png)

![Screenshot 67](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_67.png)

![Screenshot 68](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_68.png)

![Screenshot 69](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_69.png)

![Screenshot 70](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_70.png)

![Screenshot 71](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_71.png)

![Screenshot 74](C:/PythonProject/TECH_modul/skriny%20TECH_modul/Screenshot_74.png)

### Dodatkowe screeny aplikacji

Pełny katalog screenów do konsultacji:
- `C:\PythonProject\TECH_modul\docs\consultation_pack\screens\`
- `C:\PythonProject\TECH_modul\docs\consultation_pack\screens_full\`

Pełny indeks screenów:
- `C:\PythonProject\TECH_modul\docs\consultation_pack\SCREENS_FULL_INDEX.md`

## Jakich wynikow oczekujemy

Najpierw:
- analiza plikow,
- analiza obecnego UI,
- wskazanie plikow do zmiany.

Potem:
- plan wdrozenia,
- krok po kroku.

Na koncu:
- konkretne zmiany w kodzie.

## Krótkie zadanie dla modelu

Przeanalizuj pakiet screenow i strukture programu TECH_modul. Skup sie na zakladce `Wycena`, ktora ma byc glownym miejscem pracy dla importu 3D, mapowania, wyceny i rozkroju. Najpierw pokaz analize plikow, potem plan, potem wdrozenie. Analizuj tylko zalaczone materialy i nie zgaduj, jesli cos mozna sprawdzic w kodzie.

