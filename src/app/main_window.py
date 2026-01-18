from PySide6 import QtWidgets


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        # ATTACH_MODULE_DB_FALLBACK_V1
        # Ensure ctx.db exists (SQLite fallback) so MODUL can save/load.
        try:
            from app.module_db import ModuleDB
            if self.ctx is not None and getattr(self.ctx, 'db', None) is None:
                self.ctx.db = ModuleDB()
        except Exception:
            pass
        self.setWindowTitle("TECH — Kalkulator (GUI)")

        self.tabs = QtWidgets.QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self._build_tabs()

        self.resize(1200, 800)
        self.show()

        # AUTO_SWITCH_MODUL_V1
        bus = None
        try:
            if isinstance(self.ctx, dict):
                bus = self.ctx.get('bus')
            else:
                bus = getattr(self.ctx, 'bus', None)
        except Exception:
            bus = None
        if bus is not None and hasattr(bus, 'module_load_requested'):
            try:
                bus.module_load_requested.connect(lambda *_: self.tabs.setCurrentIndex(0))
            except Exception:
                pass

    def _build_tabs(self):
        # Buduj zakładki bezpiecznie: jak jedna padnie, reszta ma działać.
        self.tabs.clear()
        from tabs.registry import build_tabs
        for title, widget in build_tabs(self.ctx):
            if widget is None:
                continue
            # TAB_LABEL_FALLBACK_V1
            label = str(title).strip() if title is not None else ""
            if not label:
                try:
                    label = str(widget.windowTitle() or "").strip()
                except Exception:
                    label = ""
            if not label:
                try:
                    label = str(widget.objectName() or "").strip()
                except Exception:
                    label = ""
            if not label:
                label = widget.__class__.__name__
            self.tabs.addTab(widget, label)

