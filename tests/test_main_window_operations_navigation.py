from src.app.main_window import MainWindow


class _OpsStub:
    def __init__(self) -> None:
        self.payload = None

    def navigate_to_context(self, payload):
        self.payload = dict(payload or {})


def test_main_window_navigate_to_operations_delegates():
    win = MainWindow.__new__(MainWindow)
    ops = _OpsStub()
    called = {"tab": None}
    win._tabs_by_title = {"OPERACJE": ops}
    win._navigate_to_tab = lambda title: called.update({"tab": title})
    win._show_runtime_error = lambda *_a, **_k: None

    MainWindow.navigate_to_operations(win, {"point_id": "point-1", "target_tab": "mapa_zlecen"})

    assert called["tab"] == "OPERACJE"
    assert ops.payload is not None
    assert ops.payload.get("point_id") == "point-1"
