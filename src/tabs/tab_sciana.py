from PySide6 import QtWidgets

class ScianaTab(QtWidgets.QWidget):
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("ŚCIANA (placeholder) — później rozwiniemy."))
