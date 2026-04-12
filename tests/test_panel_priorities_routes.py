from datetime import date

from PyQt6.QtWidgets import QApplication

from src.core.operations_models import IssueRecord
from src.core.operations_store import OperationsStore
from src.tabs.operations_hub.panel_priorities_routes import PrioritiesRoutesPanel


def test_priorities_scoring_and_sort(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    store.add_issue(
        IssueRecord(
            title="Temat A",
            area="finanse",
            issue_type="blokada_faktury",
            priority_manual="normalny",
            status="nowe",
            project_name="P-A",
            client_name="K-A",
            blocks_invoice=True,
            estimated_revenue_unlock=1000.0,
            estimated_time_minutes=30,
            due_date=date.today().strftime("%Y-%m-%d"),
        )
    )
    store.add_issue(
        IssueRecord(
            title="Temat B",
            area="produkcja",
            issue_type="inne",
            priority_manual="niski",
            status="nowe",
            project_name="P-B",
            client_name="K-B",
            estimated_time_minutes=240,
        )
    )
    app = QApplication.instance() or QApplication([])
    _ = app
    panel = PrioritiesRoutesPanel(store=store)
    panel.refresh_data()
    assert panel.tbl_priority.rowCount() == 2
    first_score = float(panel.tbl_priority.item(0, 0).text())
    second_score = float(panel.tbl_priority.item(1, 0).text())
    assert first_score >= second_score


def test_create_route_from_selected_issue(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    store = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    store.add_issue(
        IssueRecord(
            title="Montaż X",
            area="montaz",
            issue_type="blokada_montazu",
            status="nowe",
            project_name="PX",
            client_name="CX",
            city="Krakow",
            address="ul. A 1",
        )
    )
    app = QApplication.instance() or QApplication([])
    _ = app
    panel = PrioritiesRoutesPanel(store=store)
    panel.refresh_data()
    assert panel.tbl_priority.rowCount() == 1
    panel.tbl_priority.selectRow(0)
    panel.p_crew.setText("Ekipa M")
    panel.p_group.setText("KRK-M")
    panel._on_create_route_from_selected_issue()
    panel.refresh_data()
    assert panel.tbl_routes.rowCount() == 1
