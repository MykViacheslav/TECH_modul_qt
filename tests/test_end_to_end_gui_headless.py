def test_main_window_headless_no_display():
    # Basic sanity check to ensure the GUI can be instantiated in headless mode
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv or [])
    from src.app.main_window import MainWindow
    w = MainWindow()
    assert w is not None
    w.close()
