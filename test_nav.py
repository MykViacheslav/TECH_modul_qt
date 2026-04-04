import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['TECH_MODUL_DATA_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
app = QApplication(sys.argv)

from src.app.main_window import MainWindow
w = MainWindow()
print('MainWindow OK')
w.show()

def test():
    try:
        print('=== Firma (group 3) ===')
        w._set_active_group(3)
        app.processEvents()
        print('Firma activated')
        for t in ['Dashboard','Stanowiska','ALARMY','Zakupy','Kalendarz','Czas pracy','Wydatki stale firmy','Wydatki zmienne','Pracownik']:
            try:
                w._navigate_to_tab(t)
                app.processEvents()
                print(f'  {t}: OK')
            except Exception as e:
                print(f'  {t}: CRASH -> {e}')
                traceback.print_exc()
        print('=== Projekt (group 2) ===')
        w._set_active_group(2)
        app.processEvents()
        for t in ['Modul','Komplet','Sciana']:
            try:
                w._navigate_to_tab(t)
                app.processEvents()
                print(f'  {t}: OK')
            except Exception as e:
                print(f'  {t}: CRASH -> {e}')
                traceback.print_exc()
        print()
        print('ALL DONE - no crash')
    except Exception as e:
        print(f'GLOBAL: {e}')
        traceback.print_exc()
    finally:
        app.quit()

QTimer.singleShot(1000, test)
app.exec()
