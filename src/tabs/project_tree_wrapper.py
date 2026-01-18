from __future__ import annotations
from PySide6 import QtCore, QtWidgets
from .project_tree import ProjectTree

def wrap_with_project_tree(widget: QtWidgets.QWidget, ctx):
    box = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)

    split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
    split.setChildrenCollapsible(False)

    tree = ProjectTree(ctx)
    tree.setMinimumWidth(280)

    split.addWidget(tree)
    split.addWidget(widget)
    split.setStretchFactor(0, 0)
    split.setStretchFactor(1, 1)
    split.setSizes([320, 1000])

    lay.addWidget(split)
    return box
