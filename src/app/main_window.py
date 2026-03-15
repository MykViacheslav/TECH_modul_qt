from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QPushButton, QTabWidget, QWidget

from src.tabs.registry import build_tabs


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TECH_modul")
        self.resize(1400, 900)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self._tabs_by_title = {}
        self._nav_history: list[int] = []
        self._nav_history_pos = -1
        self._is_history_navigation = False

        for title_pl, widget in build_tabs():
            self.tabs.addTab(widget, title_pl)
            self._tabs_by_title[title_pl] = widget

        self._build_tab_navigation()
        self.tabs.currentChanged.connect(self._on_current_tab_changed)
        if self.tabs.count() > 0:
            self._nav_history = [self.tabs.currentIndex()]
            self._nav_history_pos = 0
        self._update_navigation_buttons()

        self._wire_cross_tab_signals()

    def _build_tab_navigation(self) -> None:
        nav = QWidget(self.tabs)
        row = QHBoxLayout(nav)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.btn_nav_back = QPushButton("<", nav)
        self.btn_nav_forward = QPushButton(">", nav)
        self.btn_nav_home = QPushButton("Start", nav)

        for button, tooltip, width in (
            (self.btn_nav_back, "Wroc do poprzedniego kroku", 34),
            (self.btn_nav_forward, "Przejdz do nastepnego kroku", 34),
            (self.btn_nav_home, "Wroc na ekran startowy", 68),
        ):
            button.setMinimumWidth(width)
            button.setMaximumWidth(width)
            button.setToolTip(tooltip)
            row.addWidget(button, 0)

        self.btn_nav_back.clicked.connect(self._go_back)
        self.btn_nav_forward.clicked.connect(self._go_forward)
        self.btn_nav_home.clicked.connect(self._go_home)

        self.tabs.setCornerWidget(nav, Qt.Corner.TopRightCorner)

    def _on_current_tab_changed(self, index: int) -> None:
        if index < 0:
            return

        if self._is_history_navigation:
            self._update_navigation_buttons()
            return

        if self._nav_history_pos >= 0 and self._nav_history[self._nav_history_pos] == int(index):
            self._update_navigation_buttons()
            return

        if self._nav_history_pos < len(self._nav_history) - 1:
            self._nav_history = self._nav_history[: self._nav_history_pos + 1]

        self._nav_history.append(int(index))
        self._nav_history_pos = len(self._nav_history) - 1
        self._update_navigation_buttons()

    def _set_current_tab_index(self, index: int) -> None:
        if index < 0 or index >= self.tabs.count():
            return
        self._is_history_navigation = True
        try:
            self.tabs.setCurrentIndex(int(index))
        finally:
            self._is_history_navigation = False
        self._update_navigation_buttons()

    def _update_navigation_buttons(self) -> None:
        can_go_back = self._nav_history_pos > 0
        can_go_forward = 0 <= self._nav_history_pos < (len(self._nav_history) - 1)
        current_title = self.tabs.tabText(self.tabs.currentIndex()) if self.tabs.currentIndex() >= 0 else ""
        is_start = current_title == "Start"

        self.btn_nav_back.setEnabled(can_go_back)
        self.btn_nav_forward.setEnabled(can_go_forward)
        self.btn_nav_home.setEnabled(not is_start)

    def _go_back(self) -> None:
        if self._nav_history_pos <= 0:
            return
        self._nav_history_pos -= 1
        self._set_current_tab_index(self._nav_history[self._nav_history_pos])

    def _go_forward(self) -> None:
        if self._nav_history_pos < 0 or self._nav_history_pos >= len(self._nav_history) - 1:
            return
        self._nav_history_pos += 1
        self._set_current_tab_index(self._nav_history[self._nav_history_pos])

    def _go_home(self) -> None:
        tab_start = self._tabs_by_title.get("Start")
        if tab_start is None:
            return
        index = self.tabs.indexOf(tab_start)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _wire_cross_tab_signals(self) -> None:
        tab_start = self._tabs_by_title.get("Start")
        tab_nowe_zamowienie = self._tabs_by_title.get("Nowe zamowienie")
        tab_modul = self._tabs_by_title.get("Modul")
        tab_ustawienia = self._tabs_by_title.get("Ustawienia")
        tab_komplet = self._tabs_by_title.get("Komplet")
        tab_sciana = self._tabs_by_title.get("Sciana")
        tab_bazy = self._tabs_by_title.get("Bazy")

        if tab_start is not None:
            if hasattr(tab_start, "sig_new_order_requested"):
                tab_start.sig_new_order_requested.connect(self._open_new_order)
            if hasattr(tab_start, "sig_open_clients_requested"):
                tab_start.sig_open_clients_requested.connect(self._open_clients_in_bazy)
            if hasattr(tab_start, "sig_new_wall_requested"):
                tab_start.sig_new_wall_requested.connect(self._open_new_wall)
            if hasattr(tab_start, "sig_new_assembly_requested"):
                tab_start.sig_new_assembly_requested.connect(self._open_new_assembly)
            if hasattr(tab_start, "sig_new_module_requested"):
                tab_start.sig_new_module_requested.connect(self._open_new_module)
            if hasattr(tab_start, "sig_open_bazy_requested"):
                tab_start.sig_open_bazy_requested.connect(self._open_bazy)
            if hasattr(tab_start, "sig_open_settings_requested"):
                tab_start.sig_open_settings_requested.connect(self._open_settings)

        if tab_nowe_zamowienie is not None:
            if hasattr(tab_nowe_zamowienie, "sig_open_clients_base_requested"):
                tab_nowe_zamowienie.sig_open_clients_base_requested.connect(self._open_clients_in_bazy)
            if hasattr(tab_nowe_zamowienie, "sig_open_orders_base_requested"):
                tab_nowe_zamowienie.sig_open_orders_base_requested.connect(self._open_orders_in_bazy)
            if hasattr(tab_nowe_zamowienie, "sig_open_workers_base_requested"):
                tab_nowe_zamowienie.sig_open_workers_base_requested.connect(self._open_workers_in_bazy)
            if hasattr(tab_nowe_zamowienie, "sig_open_sciana_requested"):
                tab_nowe_zamowienie.sig_open_sciana_requested.connect(self._open_new_wall)
            if hasattr(tab_nowe_zamowienie, "sig_open_existing_sciana_requested"):
                tab_nowe_zamowienie.sig_open_existing_sciana_requested.connect(self._open_wall_in_sciana)

        if tab_sciana is not None and hasattr(tab_sciana, "sig_open_komplet_requested"):
            tab_sciana.sig_open_komplet_requested.connect(self._open_new_assembly)

        if tab_komplet is not None and hasattr(tab_komplet, "sig_open_order_requested"):
            tab_komplet.sig_open_order_requested.connect(self._open_new_order)

        if (
            tab_modul is not None
            and tab_ustawienia is not None
            and hasattr(tab_ustawienia, "sig_settings_saved")
            and hasattr(tab_modul, "reload_drawing_settings_from_storage")
        ):
            tab_ustawienia.sig_settings_saved.connect(tab_modul.reload_drawing_settings_from_storage)

        if (
            tab_bazy is not None
            and tab_modul is not None
            and hasattr(tab_bazy, "sig_open_module_requested")
            and hasattr(tab_modul, "load_module_from_store_name")
        ):
            tab_bazy.sig_open_module_requested.connect(self._open_module_in_modul)

        if (
            tab_bazy is not None
            and tab_sciana is not None
            and hasattr(tab_bazy, "sig_open_wall_requested")
            and hasattr(tab_sciana, "load_wall_from_store_name")
        ):
            tab_bazy.sig_open_wall_requested.connect(self._open_wall_in_sciana)

        if (
            tab_bazy is not None
            and tab_komplet is not None
            and hasattr(tab_bazy, "sig_open_assembly_requested")
            and hasattr(tab_komplet, "load_assembly_from_store_name")
        ):
            tab_bazy.sig_open_assembly_requested.connect(self._open_assembly_in_komplet)

        if tab_bazy is not None and hasattr(tab_bazy, "sig_new_module_requested"):
            tab_bazy.sig_new_module_requested.connect(self._open_new_module)

        if tab_bazy is not None and hasattr(tab_bazy, "sig_new_wall_requested"):
            tab_bazy.sig_new_wall_requested.connect(self._open_new_wall)

        if tab_bazy is not None and hasattr(tab_bazy, "sig_new_assembly_requested"):
            tab_bazy.sig_new_assembly_requested.connect(self._open_new_assembly)

    def _open_module_in_modul(self, module_name: str) -> None:
        tab_modul = self._tabs_by_title.get("Modul")
        if tab_modul is None or not hasattr(tab_modul, "load_module_from_store_name"):
            return
        loaded = bool(tab_modul.load_module_from_store_name(str(module_name or "")))
        if loaded:
            index = self.tabs.indexOf(tab_modul)
            if index >= 0:
                self.tabs.setCurrentIndex(index)

    def _open_wall_in_sciana(self, wall_name: str) -> None:
        tab_sciana = self._tabs_by_title.get("Sciana")
        if tab_sciana is None or not hasattr(tab_sciana, "load_wall_from_store_name"):
            return
        loaded = bool(tab_sciana.load_wall_from_store_name(str(wall_name or "")))
        if loaded:
            index = self.tabs.indexOf(tab_sciana)
            if index >= 0:
                self.tabs.setCurrentIndex(index)

    def _open_assembly_in_komplet(self, assembly_name: str) -> None:
        tab_komplet = self._tabs_by_title.get("Komplet")
        if tab_komplet is None or not hasattr(tab_komplet, "load_assembly_from_store_name"):
            return
        loaded = bool(tab_komplet.load_assembly_from_store_name(str(assembly_name or "")))
        if loaded:
            index = self.tabs.indexOf(tab_komplet)
            if index >= 0:
                self.tabs.setCurrentIndex(index)

    def _open_new_module(self) -> None:
        tab_modul = self._tabs_by_title.get("Modul")
        if tab_modul is None:
            return
        if hasattr(tab_modul, "start_new_module"):
            tab_modul.start_new_module()
        index = self.tabs.indexOf(tab_modul)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _open_new_wall(self, context: dict | None = None) -> None:
        tab_sciana = self._tabs_by_title.get("Sciana")
        if tab_sciana is None:
            return
        if context and hasattr(tab_sciana, "start_new_wall_from_order_context"):
            tab_sciana.start_new_wall_from_order_context(context)
        elif hasattr(tab_sciana, "start_new_wall"):
            tab_sciana.start_new_wall()
        index = self.tabs.indexOf(tab_sciana)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _open_new_assembly(self, context: dict | None = None) -> None:
        tab_komplet = self._tabs_by_title.get("Komplet")
        if tab_komplet is None:
            return
        if context and hasattr(tab_komplet, "start_new_assembly_from_wall_context"):
            tab_komplet.start_new_assembly_from_wall_context(context)
        elif hasattr(tab_komplet, "start_new_assembly"):
            tab_komplet.start_new_assembly()
        index = self.tabs.indexOf(tab_komplet)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _open_new_order(self, context: dict | None = None) -> None:
        tab_nowe_zamowienie = self._tabs_by_title.get("Nowe zamowienie")
        if tab_nowe_zamowienie is None:
            return
        if context and hasattr(tab_nowe_zamowienie, "start_new_order_from_context"):
            tab_nowe_zamowienie.start_new_order_from_context(context)
        elif hasattr(tab_nowe_zamowienie, "start_new_order"):
            tab_nowe_zamowienie.start_new_order()
        index = self.tabs.indexOf(tab_nowe_zamowienie)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _open_clients_in_bazy(self) -> None:
        tab_bazy = self._tabs_by_title.get("Bazy")
        if tab_bazy is None:
            return
        if hasattr(tab_bazy, "open_clients_tab"):
            tab_bazy.open_clients_tab(clear_form=False)
        index = self.tabs.indexOf(tab_bazy)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _open_orders_in_bazy(self) -> None:
        tab_bazy = self._tabs_by_title.get("Bazy")
        if tab_bazy is None:
            return
        if hasattr(tab_bazy, "open_orders_tab"):
            tab_bazy.open_orders_tab(clear_form=False)
        index = self.tabs.indexOf(tab_bazy)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _open_workers_in_bazy(self) -> None:
        tab_bazy = self._tabs_by_title.get("Bazy")
        if tab_bazy is None:
            return
        if hasattr(tab_bazy, "open_workers_tab"):
            tab_bazy.open_workers_tab(clear_form=False)
        index = self.tabs.indexOf(tab_bazy)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _open_bazy(self) -> None:
        tab_bazy = self._tabs_by_title.get("Bazy")
        if tab_bazy is None:
            return
        index = self.tabs.indexOf(tab_bazy)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _open_settings(self) -> None:
        tab_ustawienia = self._tabs_by_title.get("Ustawienia")
        if tab_ustawienia is None:
            return
        index = self.tabs.indexOf(tab_ustawienia)
        if index >= 0:
            self.tabs.setCurrentIndex(index)
