from PySide6 import QtWidgets

class WymiaryTab(QtWidgets.QWidget):
    """Niezalezna zakladka: Wymiary."""
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx  # moze byc None; nie mieszamy stanu miedzy tabami
        self.setObjectName("WymiaryTab")
        self.setWindowTitle("Wymiary")

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Wymiary — (do uzupelnienia logiki i UI)"))
        lay.addStretch(1)
