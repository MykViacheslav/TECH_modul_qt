from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

class StepIndicator(QFrame):
    sig_step_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StepIndicator")
        self._steps = [
            ("Sciana", "1. POMIESZCZENIE"),
            ("Modul", "2. MODUŁ"),
            ("Komplet", "3. KONFIGURACJA"),
            ("Wycena", "4. WYCENA")
        ]
        self._current_tab_key = ""
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(20, 0, 20, 0)
        self.layout.setSpacing(0)
        self.setFixedHeight(50)
        self.refresh()

    def set_current_step(self, tab_key: str):
        self._current_tab_key = tab_key
        self.refresh()

    def refresh(self):
        # Clear layout
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (key, label) in enumerate(self._steps):
            is_active = (key == self._current_tab_key)
            
            lbl = QLabel(label)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Simple logic: click takes you to tab
            lbl.mousePressEvent = lambda e, k=key: self.sig_step_clicked.emit(k)

            if is_active:
                lbl.setStyleSheet("""
                    color: #2563eb; 
                    font-weight: 900; 
                    font-size: 11px; 
                    letter-spacing: 0.1em;
                    border-bottom: 3px solid #3b82f6; 
                    padding: 10px 15px;
                """)
            else:
                lbl.setStyleSheet("""
                    color: #94a3b8; 
                    font-weight: 600; 
                    font-size: 11px; 
                    letter-spacing: 0.1em;
                    padding: 10px 15px;
                """)
            
            self.layout.addWidget(lbl)
            
            if i < len(self._steps) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color: #cbd5e1; font-size: 18px; margin: 0 5px;")
                self.layout.addWidget(sep)
        
        self.layout.addStretch(1)

    def update_style(self):
        self.setStyleSheet("QFrame#StepIndicator { background: white; border-bottom: 1px solid #e2e8f0; }")
