from __future__ import annotations

import gc

import pytest
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication


@pytest.fixture(autouse=True)
def qt_canvas_teardown():
    """Local test-only Qt teardown for heavy canvas/graphics modules."""
    yield

    app = QApplication.instance()
    if app is None:
        gc.collect()
        return

    for widget in list(app.topLevelWidgets()):
        try:
            widget.close()
        except Exception:
            pass
        try:
            widget.deleteLater()
        except Exception:
            pass

    try:
        QCoreApplication.sendPostedEvents(None, 0)
    except Exception:
        pass

    try:
        app.processEvents()
        app.processEvents()
    except Exception:
        pass

    gc.collect()
