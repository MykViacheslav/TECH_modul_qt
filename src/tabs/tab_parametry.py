from PySide6 import QtWidgets

class ParametryTab(QtWidgets.QWidget):
    """Niezalezna zakladka: Parametry."""
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setObjectName("ParametryTab")
        self.setWindowTitle("Parametry")

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Parametry — (do uzupelnienia logiki i UI)"))
        lay.addStretch(1)
