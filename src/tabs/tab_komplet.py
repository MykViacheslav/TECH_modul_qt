from PySide6 import QtWidgets

class KompletTab(QtWidgets.QWidget):
    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("KOMPLET (placeholder) — później rozwiniemy."))
