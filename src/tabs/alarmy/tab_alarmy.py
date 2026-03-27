from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.domain.alarm_models import (
    ALARM_CATEGORIES,
    ALARM_CATEGORY_LABELS,
    ALARM_SEVERITY,
    ALARM_SEVERITY_LABELS,
    AlarmDef,
    new_alarm_id,
)
from src.storage.alarm_store_json import AlarmStoreJson


class TabAlarmy(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = AlarmStoreJson()
        self._is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("ALARMY I POWIADOMIENIA", self)
        title.setStyleSheet("font-size:22px; font-weight:800;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Monitoruj braki, płatności, terminy i inne ważne zdarzenia w firmie.",
            self,
        )
        subtitle.setStyleSheet("color:#555555;")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.cb_category = QComboBox(self)
        self.cb_category.addItem("Wszystkie kategorie", "")
        for cat in ALARM_CATEGORIES:
            self.cb_category.addItem(ALARM_CATEGORY_LABELS.get(cat, cat), cat)
        filters.addWidget(QLabel("Kategoria:", self), 0)
        filters.addWidget(self.cb_category, 0)

        self.cb_severity = QComboBox(self)
        self.cb_severity.addItem("Wszystkie poziomy", "")
        for sev in ALARM_SEVERITY:
            self.cb_severity.addItem(ALARM_SEVERITY_LABELS.get(sev, sev), sev)
        filters.addWidget(QLabel("Poziom:", self), 0)
        filters.addWidget(self.cb_severity, 0)

        self.cb_status = QComboBox(self)
        self.cb_status.addItem("Aktywne", "active")
        self.cb_status.addItem("Rozwiązane", "resolved")
        self.cb_status.addItem("Wszystkie", "all")
        filters.addWidget(QLabel("Status:", self), 0)
        filters.addWidget(self.cb_status, 0)

        filters.addStretch(1)

        self.btn_refresh = QPushButton("Odswiez", self)
        self.btn_generate = QPushButton("Generuj alarmy", self)
        self.btn_clear_resolved = QPushButton("Usun rozwiazane", self)
        filters.addWidget(self.btn_refresh, 0)
        filters.addWidget(self.btn_generate, 0)
        filters.addWidget(self.btn_clear_resolved, 0)
        root.addLayout(filters)

        self.tbl = QTableWidget(0, 7, self)
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Kat.", "Poziom", "Tytul", "Opis", "Data", "Status"]
        )
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
        header = self.tbl.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setColumnWidth(0, 80)
        self.tbl.setColumnWidth(1, 100)
        self.tbl.setColumnWidth(2, 100)
        self.tbl.setColumnWidth(5, 100)
        self.tbl.setColumnWidth(6, 100)
        root.addWidget(self.tbl, 1)

        form_row = QHBoxLayout()
        form_row.setSpacing(10)

        self.ed_title = QLineEdit(self)
        self.ed_title.setPlaceholderText("Tytul alarmu")
        form_row.addWidget(QLabel("Tytul:", self), 0)
        form_row.addWidget(self.ed_title, 1)

        self.cb_new_category = QComboBox(self)
        for cat in ALARM_CATEGORIES:
            self.cb_new_category.addItem(ALARM_CATEGORY_LABELS.get(cat, cat), cat)
        form_row.addWidget(QLabel("Kat.:", self), 0)
        form_row.addWidget(self.cb_new_category, 0)

        self.cb_new_severity = QComboBox(self)
        for sev in ALARM_SEVERITY:
            self.cb_new_severity.addItem(ALARM_SEVERITY_LABELS.get(sev, sev), sev)
        form_row.addWidget(QLabel("Poziom:", self), 0)
        form_row.addWidget(self.cb_new_severity, 0)

        self.btn_add = QPushButton("Dodaj alarm", self)
        form_row.addWidget(self.btn_add, 0)
        root.addLayout(form_row)

        self.ed_description = QLineEdit(self)
        self.ed_description.setPlaceholderText("Opis alarmu (opcjonalnie)")
        root.addWidget(self.ed_description, 0)

        # === AKCJE Z ALARMU (szybkie działania) ===
        actions_frame = QFrame(self)
        actions_frame.setStyleSheet("""
            QFrame {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setSpacing(6)
        
        actions_title = QLabel("Szybkie akcje dla wybranego alarmu:", self)
        actions_title.setStyleSheet("font-weight: bold; color: #1e293b; font-size: 12px;")
        actions_layout.addWidget(actions_title)
        
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)
        
        # Alarm action buttons
        self.btn_action_purchase = QPushButton("🛒 Utwórz zakup", self)
        self.btn_action_purchase.setToolTip("Utwórz zamówienie zakupu brakującego materiału")
        self.btn_action_purchase.clicked.connect(self._action_create_purchase)
        actions_row.addWidget(self.btn_action_purchase)
        
        self.btn_action_take = QPushButton("📋 Spisz materiał", self)
        self.btn_action_take.setToolTip("Spisz materiał z magazynu dla zamówienia")
        self.btn_action_take.clicked.connect(self._action_take_material)
        actions_row.addWidget(self.btn_action_take)
        
        self.btn_action_reschedule = QPushButton("📅 Przesuń termin", self)
        self.btn_action_reschedule.setToolTip("Przesuń termin etapu zamówienia")
        self.btn_action_reschedule.clicked.connect(self._action_reschedule)
        actions_row.addWidget(self.btn_action_reschedule)
        
        self.btn_action_assign = QPushButton("👤 Przypisz pracownika", self)
        self.btn_action_assign.setToolTip("Przypisz pracownika do zamówienia")
        self.btn_action_assign.clicked.connect(self._action_assign_worker)
        actions_row.addWidget(self.btn_action_assign)
        
        self.btn_action_open_order = QPushButton("📦 Otwórz zamówienie", self)
        self.btn_action_open_order.setToolTip("Otwórz szczegóły zamówienia")
        self.btn_action_open_order.clicked.connect(self._action_open_order)
        actions_row.addWidget(self.btn_action_open_order)
        
        actions_layout.addLayout(actions_row)
        root.addWidget(actions_frame)
        
        # Standard actions row
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.btn_resolve = QPushButton("Oznacz jako rozwiazany", self)
        self.btn_delete = QPushButton("Usun", self)
        actions.addWidget(self.btn_resolve, 0)
        actions.addWidget(self.btn_delete, 0)
        actions.addStretch(1)
        root.addLayout(actions)

        self.lab_status = QLabel("", self)
        self.lab_status.setStyleSheet("color:#2d6a4f;")
        root.addWidget(self.lab_status, 0)

        self.cb_category.currentIndexChanged.connect(self._refresh_table)
        self.cb_severity.currentIndexChanged.connect(self._refresh_table)
        self.cb_status.currentIndexChanged.connect(self._refresh_table)
        self.btn_refresh.clicked.connect(self._refresh_table)
        self.btn_generate.clicked.connect(self._generate_alarms)
        self.btn_clear_resolved.clicked.connect(self._clear_resolved)
        self.btn_add.clicked.connect(self._add_alarm)
        self.btn_resolve.clicked.connect(self._resolve_selected)
        self.btn_delete.clicked.connect(self._delete_selected)

        QTimer.singleShot(100, self._refresh_table)

    def _refresh_table(self) -> None:
        self._is_loading = True
        try:
            cat_filter = str(self.cb_category.currentData() or "").strip()
            sev_filter = str(self.cb_severity.currentData() or "").strip()
            status_filter = str(self.cb_status.currentData() or "active").strip()

            alarms = self._store.list_alarms()

            if status_filter == "active":
                alarms = [a for a in alarms if not a.is_resolved]
            elif status_filter == "resolved":
                alarms = [a for a in alarms if a.is_resolved]

            if cat_filter:
                alarms = [a for a in alarms if a.category == cat_filter]
            if sev_filter:
                alarms = [a for a in alarms if a.severity == sev_filter]

            alarms.sort(key=lambda x: (x.is_resolved, -ALARM_SEVERITY.index(x.severity) if x.severity in ALARM_SEVERITY else 0))

            self.tbl.setRowCount(0)
            for alarm in alarms:
                row = self.tbl.rowCount()
                self.tbl.insertRow(row)

                id_item = QTableWidgetItem(alarm.alarm_id)
                id_item.setData(Qt.ItemDataRole.UserRole, alarm)
                self.tbl.setItem(row, 0, id_item)

                cat_label = ALARM_CATEGORY_LABELS.get(alarm.category, alarm.category)
                self.tbl.setItem(row, 1, QTableWidgetItem(cat_label))

                sev_label = ALARM_SEVERITY_LABELS.get(alarm.severity, alarm.severity)
                sev_item = QTableWidgetItem(sev_label)
                if alarm.severity == "krytyczny":
                    sev_item.setBackground(Qt.GlobalColor.red)
                    sev_item.setForeground(Qt.GlobalColor.white)
                elif alarm.severity == "ostrzezenie":
                    sev_item.setBackground(Qt.GlobalColor.yellow)
                self.tbl.setItem(row, 2, sev_item)

                self.tbl.setItem(row, 3, QTableWidgetItem(alarm.title))
                self.tbl.setItem(row, 4, QTableWidgetItem(alarm.description))

                created = alarm.created_at[:10] if alarm.created_at else "-"
                self.tbl.setItem(row, 5, QTableWidgetItem(created))

                status = "Rozwiązany" if alarm.is_resolved else "Aktywny"
                status_item = QTableWidgetItem(status)
                if alarm.is_resolved:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    status_item.setForeground(Qt.GlobalColor.darkRed)
                self.tbl.setItem(row, 6, status_item)
        finally:
            self._is_loading = False

    def _add_alarm(self) -> None:
        title = str(self.ed_title.text() or "").strip()
        if not title:
            self._set_status("Podaj tytuł alarmu.", ok=False)
            return

        category = str(self.cb_new_category.currentData() or "inne")
        severity = str(self.cb_new_severity.currentData() or "info")
        description = str(self.ed_description.text() or "").strip()

        alarm = AlarmDef(
            alarm_id=new_alarm_id(),
            category=category,
            severity=severity,
            title=title,
            description=description,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        self._store.save_alarm(alarm)
        self._set_status(f"Dodano alarm: {title}", ok=True)

        self.ed_title.clear()
        self.ed_description.clear()
        self._refresh_table()

    def _resolve_selected(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            self._set_status("Wybierz alarm do oznaczenia.", ok=False)
            return

        item = self.tbl.item(row, 0)
        if item is None:
            return
        alarm = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(alarm, AlarmDef):
            return

        self._store.resolve_alarm(alarm.alarm_id)
        self._set_status(f"Oznaczono jako rozwiązany: {alarm.title}", ok=True)
        self._refresh_table()

    def _delete_selected(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            self._set_status("Wybierz alarm do usunięcia.", ok=False)
            return

        item = self.tbl.item(row, 0)
        if item is None:
            return
        alarm = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(alarm, AlarmDef):
            return

        self._store.delete_alarm(alarm.alarm_id)
        self._set_status(f"Usunięto alarm: {alarm.title}", ok=True)
        self._refresh_table()

    def _clear_resolved(self) -> None:
        self._store.clear_resolved()
        self._set_status("Usunięto rozwiązane alarmy.", ok=True)
        self._refresh_table()

    def _generate_alarms(self) -> None:
        from src.services.alarm_generator import AlarmGenerator
        gen = AlarmGenerator()
        gen.generate_all()
        self._set_status("Wygenerowano alarmy automatyczne.", ok=True)
        self._refresh_table()
    
    def _get_selected_alarm(self) -> AlarmDef | None:
        """Get the currently selected alarm from table."""
        row = self.tbl.currentRow()
        if row < 0:
            return None
        item = self.tbl.item(row, 0)
        if item is None:
            return None
        alarm = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(alarm, AlarmDef):
            return alarm
        return None
    
    def _action_create_purchase(self) -> None:
        """Action: Create purchase order for missing material."""
        alarm = self._get_selected_alarm()
        if not alarm:
            self._set_status("Wybierz alarm najpierw.", ok=False)
            return
        
        if alarm.category != "materialy":
            self._set_status("Ta akcja jest dla alarmów materiałowych.", ok=False)
            return
        
        from src.services.material_transactions import MaterialTransactionStore
        store = MaterialTransactionStore()
        
        # Extract material info from alarm
        material_name = alarm.related_material or alarm.title.split(":")[-1].strip()
        order_code = alarm.related_order or ""
        
        tx = store.create_purchase(
            material_id="",
            material_name=material_name,
            quantity=1.0,  # Default, user should adjust
            supplier="",
            expected_date="",
            worker_name="System",
            order_code=order_code,
        )
        
        self._store.resolve_alarm(alarm.alarm_id)
        self._set_status(f"Utworzono zamówienie zakupu: {material_name} (ID: {tx.id})", ok=True)
        self._refresh_table()
    
    def _action_take_material(self) -> None:
        """Action: Take (spisz) material from stock."""
        alarm = self._get_selected_alarm()
        if not alarm:
            self._set_status("Wybierz alarm najpierw.", ok=False)
            return
        
        from src.services.material_transactions import MaterialTransactionStore
        store = MaterialTransactionStore()
        
        material_name = alarm.related_material or "Materiał"
        order_code = alarm.related_order or ""
        
        tx = store.take_material(
            material_id="",
            material_name=material_name,
            quantity=1.0,
            order_code=order_code,
            worker_name="System",
            notes=f"Spisanie z alarmu: {alarm.alarm_id}",
        )
        
        self._set_status(f"Spisano materiał: {material_name} (ID: {tx.id})", ok=True)
        self._refresh_table()
    
    def _action_reschedule(self) -> None:
        """Action: Reschedule order deadline."""
        alarm = self._get_selected_alarm()
        if not alarm:
            self._set_status("Wybierz alarm najpierw.", ok=False)
            return
        
        if alarm.category != "terminy":
            self._set_status("Ta akcja jest dla alarmów terminów.", ok=False)
            return
        
        order_code = alarm.related_order or ""
        if not order_code:
            self._set_status("Brak powiązanego zamówienia w alarmie.", ok=False)
            return
        
        # Signal to open order for rescheduling
        # In full implementation, would open a dialog
        self._set_status(f"Otwórz zamówienie {order_code}, aby przesunąć termin.", ok=True)
    
    def _action_assign_worker(self) -> None:
        """Action: Assign worker to order."""
        alarm = self._get_selected_alarm()
        if not alarm:
            self._set_status("Wybierz alarm najpierw.", ok=False)
            return
        
        order_code = alarm.related_order or ""
        if not order_code:
            self._set_status("Brak powiązanego zamówienia w alarmie.", ok=False)
            return
        
        self._set_status(f"Otwórz zamówienie {order_code}, aby przypisać pracownika.", ok=True)
    
    def _action_open_order(self) -> None:
        """Action: Open order details."""
        alarm = self._get_selected_alarm()
        if not alarm:
            self._set_status("Wybierz alarm najpierw.", ok=False)
            return
        
        order_code = alarm.related_order or ""
        if not order_code:
            self._set_status("Brak powiązanego zamówienia w alarmie.", ok=False)
            return
        
        # Try to navigate to order
        try:
            main_window = self.window()
            if hasattr(main_window, '_navigate_to_tab'):
                main_window._navigate_to_tab("Nowe zamówienie")
                self._set_status(f"Otwieram zamówienie {order_code}...", ok=True)
        except Exception:
            self._set_status(f"Zamówienie: {order_code}", ok=True)

    def _set_status(self, message: str, ok: bool) -> None:
        color = "#2d6a4f" if ok else "#b42318"
        self.lab_status.setStyleSheet(f"color:{color};")
        self.lab_status.setText(str(message or ""))

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        try:
            from src.services.alarm_generator import AlarmGenerator
            AlarmGenerator().generate_all()
        except Exception:
            pass
        self._refresh_table()
