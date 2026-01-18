from __future__ import annotations

def restore_widget_tree(root):
    """
    Restore 'collapsed/hidden' UI inside *one* tab only.
    - enables all QTabWidget tabs
    - resets QSplitters if some pane is 0px
    - expands common collapsible widgets (best-effort)
    - does NOT touch other tabs => independent
    """
    if root is None:
        return

    try:
        from PySide6 import QtWidgets
    except Exception:
        return

    try:
        root.setVisible(True)
    except Exception:
        pass

    # 1) QTabWidget (sub-tabs like Wymiary/Parametry)
    for tw in root.findChildren(QtWidgets.QTabWidget):
        try:
            if tw.tabBar():
                tw.tabBar().setVisible(True)
        except Exception:
            pass
        try:
            for i in range(tw.count()):
                try:
                    tw.setTabEnabled(i, True)
                except Exception:
                    pass
                try:
                    w = tw.widget(i)
                    if w is not None:
                        w.setVisible(True)
                except Exception:
                    pass
        except Exception:
            pass

    # 2) QStackedWidget / QToolBox (czasem używane zamiast tabów)
    for sw in root.findChildren(QtWidgets.QStackedWidget):
        try:
            if sw.count() > 0 and sw.currentIndex() < 0:
                sw.setCurrentIndex(0)
        except Exception:
            pass

    for tb in root.findChildren(QtWidgets.QToolBox):
        try:
            if tb.count() > 0 and tb.currentIndex() < 0:
                tb.setCurrentIndex(0)
        except Exception:
            pass

    # 3) Splittery: jeśli coś ma 0px -> daj sensowne rozmiary
    for sp in root.findChildren(QtWidgets.QSplitter):
        try:
            sizes = list(sp.sizes() or [])
            if not sizes:
                continue
            if sum(sizes) <= 0 or any(s <= 0 for s in sizes):
                sp.setSizes([200] * len(sizes))
        except Exception:
            pass

    # 4) Checkable groupbox -> włącz
    for gb in root.findChildren(QtWidgets.QGroupBox):
        try:
            if gb.isCheckable() and not gb.isChecked():
                gb.setChecked(True)
        except Exception:
            pass

    # 5) Best-effort expand for collapsibles (różne implementacje)
    for w in root.findChildren(QtWidgets.QWidget):
        # show hidden widgets
        try:
            if hasattr(w, "isHidden") and w.isHidden():
                w.setVisible(True)
        except Exception:
            pass

        # try common expand/collapse APIs
        for mname, arg in (
            ("setCollapsed", False),
            ("set_collapsed", False),
            ("setExpanded", True),
            ("set_expanded", True),
            ("expand", None),
            ("open", None),
        ):
            fn = getattr(w, mname, None)
            if callable(fn):
                try:
                    fn() if arg is None else fn(arg)
                except Exception:
                    pass

    try:
        root.updateGeometry()
        root.repaint()
    except Exception:
        pass
