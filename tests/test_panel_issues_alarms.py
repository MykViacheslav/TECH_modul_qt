from datetime import date

from PyQt6.QtWidgets import QApplication

from src.core.operations_models import IssueRecord
from src.core.operations_store import OperationsStore
from src.tabs.operations_hub.panel_issues_alarms import IssuesAlarmsPanel


def test_issues_panel_works_on_empty_data(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    _ = app
    panel = IssuesAlarmsPanel()
    panel.refresh_data()
    assert panel.tbl.rowCount() == 0


def test_issues_panel_filters(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    store.add_issue(
        IssueRecord(
            title="Blokada faktury",
            description="Opis A",
            area="finanse",
            issue_type="blokada_faktury",
            priority_manual="krytyczny",
            status="nowe",
            project_name="Projekt Alfa",
            client_name="Klient Test",
            owner="Anna",
            due_date=date.today().strftime("%Y-%m-%d"),
            blocks_invoice=True,
        )
    )
    app = QApplication.instance() or QApplication([])
    _ = app
    panel = IssuesAlarmsPanel(store=store)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1

    panel.f_text.setText("alfa")
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1

    panel.f_owner.setText("nie_ma")
    panel.refresh_data()
    assert panel.tbl.rowCount() == 0
