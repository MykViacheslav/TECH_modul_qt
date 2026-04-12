from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from src.core.operations_store import OperationsStore
from src.tabs.operations_hub.panel_issues_alarms import IssuesAlarmsPanel
from src.tabs.operations_hub.panel_orders_map import OrdersMapPanel
from src.tabs.operations_hub.panel_priorities_routes import PrioritiesRoutesPanel


class TabOperationsHub(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = OperationsStore()
        self._role = "biuro"
        self._worker_name = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.kpi_bar = QLabel(self)
        self.kpi_bar.setStyleSheet(
            "QLabel{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;"
            "padding:8px 10px;color:#334155;font-size:12px;font-weight:600;}"
        )
        root.addWidget(self.kpi_bar, 0)

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1)

        self.panel_issues = IssuesAlarmsPanel(self, store=self._store, on_data_changed=self._on_data_changed)
        self.panel_routes = PrioritiesRoutesPanel(self, store=self._store, on_data_changed=self._on_data_changed)
        self.panel_orders_map = OrdersMapPanel(self, operations_store=self._store, on_data_changed=self._on_data_changed)

        self.tabs.addTab(self.panel_issues, "Problemy i alarmy")
        self.tabs.addTab(self.panel_routes, "Priorytety i trasy")
        self.tabs.addTab(self.panel_orders_map, "Mapa zlecen")

        self.refresh_all()

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._worker_name = str(worker_name or "").strip()
        self._role = str(role or "").strip().lower()
        self.panel_issues.set_current_user(self._worker_name, self._role)
        self.panel_routes.set_current_user(self._worker_name, self._role)
        self.panel_orders_map.set_current_user(self._worker_name, self._role)
        self.refresh_all()

    def refresh_all(self) -> None:
        self.panel_issues.refresh_data()
        self.panel_routes.refresh_data()
        self.panel_orders_map.refresh_data()
        kpi = self._store.get_issue_kpis(role=self._role, worker_name=self._worker_name)
        self.kpi_bar.setText(
            "OPERACJE | "
            f"Otwarte: {kpi.get('otwarte', 0)} | "
            f"Krytyczne: {kpi.get('krytyczne', 0)} | "
            f"Po terminie: {kpi.get('po_terminie', 0)} | "
            f"Blokuje fakture: {kpi.get('blokuje_fakture', 0)} | "
            f"Blokuje produkcje: {kpi.get('blokuje_produkcje', 0)} | "
            f"Blokuje montaz: {kpi.get('blokuje_montaz', 0)}"
        )

    def _on_data_changed(self) -> None:
        self.refresh_all()

    def navigate_to_context(self, payload: dict | None) -> None:
        ctx = dict(payload or {})
        target = str(ctx.get("target_tab", "mapa_zlecen") or "mapa_zlecen").strip().lower()
        point_id = str(ctx.get("point_id", "") or "").strip()
        issue_id = str(ctx.get("issue_id", "") or "").strip()
        route_id = str(ctx.get("route_id", "") or "").strip()
        project_name = str(ctx.get("project_name", "") or "")
        client_name = str(ctx.get("client_name", "") or "")

        self.refresh_all()

        if target == "problemy_i_alarmy":
            self.tabs.setCurrentWidget(self.panel_issues)
            self.panel_issues.navigate_to_issue(
                issue_id=issue_id,
                project_name=project_name,
                client_name=client_name,
            )
            return

        if target == "priorytety_i_trasy":
            self.tabs.setCurrentWidget(self.panel_routes)
            self.panel_routes.navigate_to_route_or_issue(
                route_id=route_id,
                issue_id=issue_id,
                project_name=project_name,
                client_name=client_name,
            )
            return

        # Default: mapa zlecen
        self.tabs.setCurrentWidget(self.panel_orders_map)
        self.panel_orders_map.navigate_to_point(
            point_id=point_id,
            project_name=project_name,
            client_name=client_name,
        )
