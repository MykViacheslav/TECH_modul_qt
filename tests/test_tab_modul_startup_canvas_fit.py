from PyQt6.QtWidgets import QApplication


def test_tab_modul_run_startup_canvas_fit_calls_render_with_fit_true(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    calls = []

    def fake_render_module(draft, fit=False, selected_part_key=""):
        calls.append({
            "draft": draft,
            "fit": fit,
            "selected_part_key": selected_part_key,
        })

    w.canvas.render_module = fake_render_module
    w._startup_canvas_fit_done = False

    w._run_startup_canvas_fit()

    assert w._startup_canvas_fit_done is True
    assert len(calls) == 1
    assert calls[0]["fit"] is True
    assert calls[0]["draft"] is w._draft
    assert calls[0]["selected_part_key"] == getattr(w, "_selected_part_key", "")


def test_tab_modul_run_startup_canvas_fit_runs_only_once(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    calls = []

    def fake_render_module(draft, fit=False, selected_part_key=""):
        calls.append({
            "draft": draft,
            "fit": fit,
            "selected_part_key": selected_part_key,
        })

    w.canvas.render_module = fake_render_module
    w._startup_canvas_fit_done = False

    w._run_startup_canvas_fit()
    w._run_startup_canvas_fit()

    assert len(calls) == 1