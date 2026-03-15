from PyQt6.QtWidgets import QApplication

from src.domain.module_models import PartDef


def test_tab_modul_choose_startup_selected_part_key_prefers_front(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w._draft.parts = {
        "side_left": PartDef(key="side_left", name_pl="Bok lewy"),
        "front__front": PartDef(key="front__front", name_pl="Front"),
        "top": PartDef(key="top", name_pl="Wieniec gorny"),
    }

    assert w._choose_startup_selected_part_key() == "front__front"


def test_tab_modul_choose_startup_selected_part_key_falls_back_to_side_left(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w._draft.parts = {
        "side_left": PartDef(key="side_left", name_pl="Bok lewy"),
        "top": PartDef(key="top", name_pl="Wieniec gorny"),
    }

    assert w._choose_startup_selected_part_key() == "side_left"


def test_tab_modul_run_startup_canvas_fit_uses_preferred_selected_part(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w._draft.parts = {
        "side_left": PartDef(key="side_left", name_pl="Bok lewy"),
        "front__front": PartDef(key="front__front", name_pl="Front"),
    }

    selected_calls = []
    render_calls = []

    def fake_select_part(key: str) -> None:
        selected_calls.append(key)

    def fake_render_module(draft, fit=False, selected_part_key=""):
        render_calls.append({
            "draft": draft,
            "fit": fit,
            "selected_part_key": selected_part_key,
        })

    w.tree.select_part = fake_select_part
    w.canvas.render_module = fake_render_module
    w._startup_canvas_fit_done = False

    w._run_startup_canvas_fit()

    assert w._selected_part_key == "front__front"
    assert selected_calls == ["front__front"]
    assert len(render_calls) == 1
    assert render_calls[0]["fit"] is True
    assert render_calls[0]["selected_part_key"] == "front__front"